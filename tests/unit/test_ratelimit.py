"""Tests for the MySQL-backed per-IP rate limits (ken #1250).

The pure parts (limit parsing, counter arithmetic) run without a database; the rest uses
the test DB (``rate_limit_hits``), like the code in production.
"""

import pymysql
import pytest
from flask import Flask, Response, jsonify

from dashboard import ratelimit
from dashboard.errors import register_error_handlers

NOW = 1_800_000_000  # a fixed clock: 1_800_000_000 % 3600 == 0, start of an hour

# -- pure ---------------------------------------------------------------------


def test_parse_limits() -> None:
    limits = ratelimit.parse_limits("5 per minute; 20 per hour")
    assert [(lim.amount, lim.period, str(lim)) for lim in limits] == [
        (5, 60, "5 per minute"),
        (20, 3600, "20 per hour"),
    ]
    assert ratelimit.parse_limits("1 per days")[0].period == 86400


@pytest.mark.parametrize("spec", ["", "5/minute", "five per hour", "0 per hour"])
def test_parse_limits_rejects_garbage(spec: str) -> None:
    with pytest.raises(ValueError, match="invalid rate limit"):
        ratelimit.parse_limits(spec)


def _counter(amount: int, period: int, hits: int) -> ratelimit.Counter:
    limit = ratelimit.Limit(amount, period, f"{amount} per {period}s")
    return ratelimit.Counter(limit, "b", NOW, hits)


def test_counter_arithmetic() -> None:
    c = _counter(5, 60, 6)
    assert (c.remaining, c.reset, c.breached) == (0, NOW + 60, True)
    assert not _counter(5, 60, 5).breached


def test_tightest_prefers_breached_then_fewest_remaining() -> None:
    minute, hour = _counter(5, 60, 2), _counter(20, 3600, 19)
    assert ratelimit._tightest([minute, hour]) is hour
    breached = _counter(5, 60, 6)
    assert ratelimit._tightest([breached, hour]) is breached


# -- against the test DB ------------------------------------------------------


@pytest.fixture
def limited(db, monkeypatch):
    """Counters reset, clock frozen at ``NOW``; yields an app factory."""
    monkeypatch.setattr(ratelimit, "_now", lambda: NOW)
    ratelimit.reset()
    breaches: list[str] = []

    def make_app() -> Flask:
        """One app = one gunicorn worker: separate process state, same DB."""
        app = Flask(__name__)
        ratelimit.init_rate_limit(app)
        register_error_handlers(app, debug=False)

        @app.route("/api/v1/thing", methods=["POST"])
        @ratelimit.rate_limit(
            "2 per minute", on_breach=lambda lim: breaches.append(str(lim))
        )
        def thing() -> Response:
            return jsonify(ok=True)

        @app.route("/api/v1/other", methods=["POST"])
        @ratelimit.rate_limit("2 per minute")
        def other() -> Response:
            return jsonify(ok=True)

        @app.route("/free", methods=["POST"])
        @ratelimit.rate_limit(
            "1 per minute", deduct_when=lambda r: r.status_code != 302
        )
        def free() -> tuple[str, int]:
            return "", 302

        @app.route("/page", methods=["POST"])
        @ratelimit.rate_limit("1 per minute")
        def page() -> str:
            return "ok"

        return app

    make_app.breaches = breaches  # type: ignore[attr-defined]
    yield make_app
    ratelimit.reset()


def _hits(db) -> dict[str, int]:
    with db.cursor() as cur:
        cur.execute("SELECT bucket, hits FROM rate_limit_hits")
        return {row["bucket"]: row["hits"] for row in cur.fetchall()}


def test_third_request_is_rejected_with_json_and_headers(limited, db) -> None:
    client = limited().test_client()
    first = client.post("/api/v1/thing")
    assert first.status_code == 200
    assert first.headers["X-RateLimit-Remaining"] == "1"
    assert client.post("/api/v1/thing").status_code == 200
    r = client.post("/api/v1/thing")
    assert r.status_code == 429
    assert r.get_json() == {"error": "Rate limit exceeded: 2 per minute"}
    assert r.headers["X-RateLimit-Limit"] == "2"
    assert r.headers["X-RateLimit-Remaining"] == "0"
    assert r.headers["X-RateLimit-Reset"] == str(NOW + 60)
    assert r.headers["Retry-After"] == "60"
    assert limited.breaches == ["2 per minute"]
    # The rejected request was given back: the counter stays at the limit.
    assert list(_hits(db).values()) == [2]


def test_limit_is_shared_between_workers(limited) -> None:
    """The bug of #1250: memory:// gave each gunicorn worker its own budget."""
    workers = [limited().test_client() for _ in range(4)]
    statuses = [workers[i % 4].post("/api/v1/thing").status_code for i in range(4)]
    assert statuses == [200, 200, 429, 429]


def test_each_view_has_its_own_budget(limited) -> None:
    client = limited().test_client()
    for _ in range(2):
        client.post("/api/v1/thing")
    assert client.post("/api/v1/other").status_code == 200


def test_deduct_when_false_gives_the_request_back(limited) -> None:
    client = limited().test_client()
    assert [client.post("/free").status_code for _ in range(5)] == [302] * 5


def test_next_window_starts_from_zero_and_purges_old_rows(
    limited, db, monkeypatch
) -> None:
    client = limited().test_client()
    for _ in range(3):
        client.post("/api/v1/thing")
    monkeypatch.setattr(ratelimit, "_now", lambda: NOW + 60)
    assert client.post("/api/v1/thing").status_code == 200
    with db.cursor() as cur:
        cur.execute("SELECT window_start, hits FROM rate_limit_hits")
        assert [(r["window_start"], r["hits"]) for r in cur.fetchall()] == [
            (NOW + 60, 1)
        ]


def test_disabled_touches_nothing(limited, db) -> None:
    app = limited()
    app.config["RATELIMIT_ENABLED"] = False
    client = app.test_client()
    assert [client.post("/api/v1/thing").status_code for _ in range(4)] == [200] * 4
    assert _hits(db) == {}


def test_storage_error_fails_open(limited, monkeypatch) -> None:
    client = limited().test_client()

    def down() -> None:
        raise pymysql.err.OperationalError(2003, "Can't connect")

    with monkeypatch.context() as mp:  # undone before the fixture's reset()
        mp.setattr(ratelimit.db, "get_connection", down)
        statuses = [client.post("/api/v1/thing").status_code for _ in range(4)]
    assert statuses == [200] * 4


def test_failing_query_fails_open_and_failed_refund_still_rejects(
    limited, monkeypatch
) -> None:
    """A DB error mid-way is logged; it never turns into a 500."""
    client = limited().test_client()
    real = ratelimit.db.load_queries

    class Broken:
        def __init__(self, fail: str) -> None:
            self.queries, self.fail = real(), fail

        def __getattr__(self, name: str):
            if name == self.fail:
                raise pymysql.err.OperationalError(1146, "no such table")
            return getattr(self.queries, name)

    with monkeypatch.context() as mp:
        mp.setattr(ratelimit.db, "load_queries", lambda: Broken("rl_hit"))
        assert client.post("/api/v1/thing").status_code == 200
    for _ in range(2):
        client.post("/api/v1/thing")
    with monkeypatch.context() as mp:
        mp.setattr(ratelimit.db, "load_queries", lambda: Broken("rl_refund"))
        assert client.post("/api/v1/thing").status_code == 429


def test_browser_gets_the_default_html_429(limited) -> None:
    client = limited().test_client()
    client.post("/page", headers={"Accept": "text/html"})
    r = client.post("/page", headers={"Accept": "text/html"})
    assert r.status_code == 429
    assert r.mimetype == "text/html"
    assert r.headers["Retry-After"] == "60"
