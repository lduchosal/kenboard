"""Per-IP rate limits shared by every gunicorn worker (ken #1250).

Replaces flask-limiter, whose ``memory://`` storage kept one counter per worker
process: under ``gunicorn --workers 4`` an attacker spread over the workers got up
to 4x the configured budget. Counters now live in MySQL (``rate_limit_hits``), the
one store every worker already shares — no Redis to deploy.

Usage::

    @bp.route("/login", methods=["POST"])
    @rate_limit("5 per minute; 20 per hour", deduct_when=..., on_breach=...)
    def login_post(): ...

Semantics
    - **Fixed windows** (flask-limiter's default strategy): ``5 per minute`` allows
      5 requests per calendar minute of the epoch. Limits separated by ``;`` are
      AND-combined. Units: second, minute, hour, day.
    - One bucket per (view, limit): two views never share a budget.
    - **Count first, then decide.** Each request increments its counters atomically
      before the view runs and is rejected with 429 when a counter goes over the
      limit (rejected requests are given back). Parallel requests therefore cannot
      slip through between a check and a hit.
    - ``deduct_when(response)`` — when it returns False the request is given back
      after the view ran (``/login``: a successful login does not burn the budget).
    - ``on_breach(limit)`` — called with the limit that was hit, before the 429.
    - Headers ``X-RateLimit-Limit`` / ``-Remaining`` / ``-Reset`` (epoch) on every
      limited response, plus ``Retry-After`` on the 429 — added by an
      ``after_request`` hook so error handlers that re-render a page keep them.
    - ``app.config["RATELIMIT_ENABLED"] = False`` turns every limit off (tests).
    - **Fails open**: a storage error is logged (``ratelimit.storage_error``) and the
      request goes through. The limit is defence in depth; it must not take login
      down with it (e.g. migration 0023 not applied yet).
"""

from __future__ import annotations

import functools
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ParamSpec, TypeVar

import pymysql
from flask import Flask, Response, current_app, g, make_response, request
from werkzeug.exceptions import TooManyRequests

from dashboard import db
from dashboard.logging import get_logger

ENABLED_KEY = "RATELIMIT_ENABLED"
_UNITS = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}
_LIMIT_RE = re.compile(r"^\s*(\d+)\s+per\s+(second|minute|hour|day)s?\s*$")
_BUCKET_MAX = 160
_CLIENT_MAX = 64

log = get_logger("ratelimit")
P = ParamSpec("P")
T = TypeVar("T")


@dataclass(frozen=True)
class Limit:
    """``amount`` requests per ``period`` seconds."""

    amount: int
    period: int
    text: str

    def __str__(self) -> str:
        """Human form, as written in the decorator (``5 per minute``)."""
        return self.text


@dataclass(frozen=True)
class Counter:
    """State of one limit for the current request."""

    limit: Limit
    bucket: str
    window_start: int
    hits: int

    @property
    def remaining(self) -> int:
        """Requests left in this window."""
        return max(self.limit.amount - self.hits, 0)

    @property
    def reset(self) -> int:
        """Epoch second at which this window ends."""
        return self.window_start + self.limit.period

    @property
    def breached(self) -> bool:
        """Whether this request went over the limit."""
        return self.hits > self.limit.amount


def parse_limits(spec: str) -> tuple[Limit, ...]:
    """Parse ``"5 per minute; 20 per hour"`` into limits.

    Raises:
        ValueError: a part is not ``<N> per <unit>`` or ``N`` is 0.
    """
    limits = []
    for part in spec.split(";"):
        match = _LIMIT_RE.match(part)
        if match is None or int(match.group(1)) == 0:
            msg = f"invalid rate limit {part.strip()!r} (expected '<N> per <unit>')"
            raise ValueError(msg)
        limits.append(Limit(int(match.group(1)), _UNITS[match.group(2)], part.strip()))
    return tuple(limits)


def _now() -> int:
    """Current epoch second (one clock for every worker of the host)."""
    return int(time.time())


def client_ip() -> str:
    """Caller IP (real client behind the proxy: ``ProxyFix`` runs first)."""
    return (request.remote_addr or "unknown")[:_CLIENT_MAX]


def _storage(action: Callable[[pymysql.Connection, db.Queries], T]) -> T | None:
    """Run ``action(conn, queries)`` on a fresh connection; ``None`` on DB error."""
    try:
        conn = db.get_connection()
        try:
            return action(conn, db.load_queries())
        finally:
            conn.close()
    except pymysql.Error as exc:
        log.exception("ratelimit.storage_error", error=str(exc))
        return None


def _take(prefix: str, limits: tuple[Limit, ...], now: int) -> list[Counter] | None:
    """Count this request against each limit; ``None`` on storage error."""
    client = client_ip()

    def action(conn: pymysql.Connection, queries: db.Queries) -> list[Counter]:
        """Increment then read back each counter of this request."""
        counters = []
        for limit in limits:
            bucket = f"{prefix}:{limit.amount}/{limit.period}"[-_BUCKET_MAX:]
            start = now - now % limit.period
            key = {"bucket": bucket, "client": client, "window_start": start}
            queries.rl_hit(conn, expires_at=start + limit.period, **key)
            hits = int(queries.rl_hits(conn, **key) or 0)
            counters.append(Counter(limit, bucket, start, hits))
        if any(c.hits == 1 for c in counters):  # a new window opened: tidy up
            queries.rl_purge(conn, now=now)
        return counters

    return _storage(action)


def _refund(counters: list[Counter]) -> None:
    """Give back the request counted by ``_take`` (best effort)."""
    client = client_ip()

    def action(conn: pymysql.Connection, queries: db.Queries) -> None:
        """Decrement each counter of this request."""
        for c in counters:
            queries.rl_refund(
                conn, bucket=c.bucket, client=client, window_start=c.window_start
            )

    _storage(action)


def _tightest(counters: list[Counter]) -> Counter:
    """The counter to advertise: the breached one, else the fewest remaining."""
    breached = [c for c in counters if c.breached]
    if breached:
        return max(breached, key=lambda c: c.reset)
    return min(counters, key=lambda c: (c.remaining, -c.reset))


def rate_limit(
    spec: str,
    *,
    deduct_when: Callable[[Response], bool] | None = None,
    on_breach: Callable[[Limit], None] | None = None,
) -> Callable[[Callable[P, Any]], Callable[P, Response]]:
    """Decorate a view with the per-IP limits of ``spec`` (see module doc)."""
    limits = parse_limits(spec)

    def decorator(view: Callable[P, Any]) -> Callable[P, Response]:
        """Wrap ``view``; its bucket prefix is its dotted name."""
        prefix = f"{view.__module__}.{view.__qualname__}"

        @functools.wraps(view)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> Response:
            """Count, reject with 429 or run the view, then maybe give back.

            Raises:
                TooManyRequests: a limit of ``spec`` is exceeded for this IP.
            """
            if not current_app.config.get(ENABLED_KEY, True):
                return make_response(view(*args, **kwargs))
            now = _now()
            counters = _take(prefix, limits, now)
            if counters is None:
                return make_response(view(*args, **kwargs))
            tightest = _tightest(counters)
            g.rate_limit = (tightest, now)
            if tightest.breached:
                _refund(counters)
                if on_breach is not None:
                    on_breach(tightest.limit)
                raise TooManyRequests(
                    description=f"Rate limit exceeded: {tightest.limit}",
                    retry_after=tightest.reset - now,
                )
            response = make_response(view(*args, **kwargs))
            if deduct_when is not None and not deduct_when(response):
                _refund(counters)
            return response

        return wrapper

    return decorator


def _add_headers(response: Response) -> Response:
    """Expose the tightest limit of a rate-limited request in its headers."""
    state: tuple[Counter, int] | None = g.pop("rate_limit", None)
    if state is not None:
        counter, now = state
        response.headers["X-RateLimit-Limit"] = str(counter.limit.amount)
        response.headers["X-RateLimit-Remaining"] = str(counter.remaining)
        response.headers["X-RateLimit-Reset"] = str(counter.reset)
        if response.status_code == TooManyRequests.code:
            response.headers["Retry-After"] = str(max(counter.reset - now, 1))
    return response


def init_rate_limit(app: Flask) -> None:
    """Register the header hook; limits are on unless ``RATELIMIT_ENABLED`` is False."""
    app.config.setdefault(ENABLED_KEY, True)
    app.after_request(_add_headers)


def reset() -> None:
    """Forget every counter (tests; or clearing a lock-out by hand)."""
    conn = db.get_connection()
    try:
        db.load_queries().rl_reset(conn)
    finally:
        conn.close()
