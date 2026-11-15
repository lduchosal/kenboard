"""Non-regression tests for the #1183 security audit (tasks #1184-#1195).

Every test here runs with authentication really enforced (``LOGIN_DISABLED`` off) — the
default test app bypasses it, which is exactly how these holes went unnoticed.
"""

import hashlib
import uuid

import pytest
from argon2 import PasswordHasher

from dashboard.config import Config

ORIGIN = {"Origin": "http://localhost"}
PW = "correct horse battery staple 42!"
_hasher = PasswordHasher()


@pytest.fixture
def auth_app(app, db):
    """The test app with authentication really enforced."""
    app.config["LOGIN_DISABLED"] = False
    yield app
    app.config["LOGIN_DISABLED"] = True


def mk_user(db, queries, name, *, admin=False, email=None):
    """Insert a user with the shared test password; return its id."""
    uid = str(uuid.uuid4())
    queries.usr_create(
        db,
        id=uid,
        name=name,
        email=email,
        color="#0969da",
        password_hash=_hasher.hash(PW),
        is_admin=int(admin),
    )
    return uid


def mk_cat(db, queries, name):
    """Insert a category; return its id."""
    cid = str(uuid.uuid4())
    queries.cat_create(db, id=cid, name=name, color="#abcdef", position=0)
    return cid


def mk_proj(db, queries, cat, name):
    """Insert a project in ``cat``; return its id."""
    pid = str(uuid.uuid4())
    queries.proj_create(
        db,
        id=pid,
        cat_id=cat,
        name=name,
        acronym="P",
        status="active",
        position=0,
        default_who="",
    )
    return pid


def mk_task(db, queries, proj, title, desc="secret"):
    """Insert a task in ``proj``; return its id."""
    queries.task_create(
        db,
        project_id=proj,
        title=title,
        description=desc,
        attachement=None,
        status="todo",
        who="x",
        due_date=None,
        position=0,
    )
    cur = db.cursor()
    cur.execute("SELECT LAST_INSERT_ID() AS i")
    return cur.fetchone()["i"]


def mk_key(db, queries, proj, scope="write", user_id=None):
    """Insert an api_key scoped on ``proj``; return ``(bearer headers, key id)``."""
    plain = "kb_" + uuid.uuid4().hex
    kid = str(uuid.uuid4())
    queries.key_create(
        db,
        id=kid,
        user_id=user_id,
        key_type=None,
        key_hash=hashlib.sha256(plain.encode()).hexdigest(),
        label="sec-audit",
        expires_at=None,
    )
    queries.key_scopes_add(db, api_key_id=kid, project_id=proj, scope=scope)
    return {"Authorization": f"Bearer {plain}"}, kid


def login(app, name):
    """Return a test client logged in as ``name`` through the real /login form."""
    client = app.test_client()
    resp = client.post("/login", data={"name": name, "password": PW})
    assert resp.status_code == 302
    return client


# -- #1184 — emailed links must not follow client-supplied headers ------------


@pytest.fixture
def sent_mail(monkeypatch):
    """Capture ``send_email`` kwargs instead of talking to an SMTP server."""
    import dashboard.email as email_mod

    sent: dict = {}
    monkeypatch.setattr(email_mod, "send_email", lambda **kw: sent.update(kw) or True)
    return sent


class TestEmailedLinkHost:
    """#1184 — the host of an emailed link is not attacker-controlled."""

    def test_reset_link_ignores_x_forwarded_host(
        self, auth_app, db, queries, sent_mail
    ):
        """``X-Forwarded-Host`` must not decide where the reset link points."""
        mk_user(db, queries, "victim", email="victim@example.org")
        auth_app.test_client().post(
            "/forgot-password",
            data={"email": "victim@example.org"},
            headers={"X-Forwarded-Host": "evil.example"},
        )
        assert sent_mail["reset_url"].startswith("http://localhost/reset-password/")

    def test_reset_link_ignores_exotic_forwarded_proto(
        self, auth_app, db, queries, sent_mail
    ):
        """A scheme other than http/https in ``X-Forwarded-Proto`` is ignored."""
        mk_user(db, queries, "victim", email="victim@example.org")
        auth_app.test_client().post(
            "/forgot-password",
            data={"email": "victim@example.org"},
            headers={"X-Forwarded-Proto": "javascript"},
        )
        assert sent_mail["reset_url"].startswith("http://localhost/")

    def test_base_url_setting_wins_over_host(
        self, auth_app, db, queries, sent_mail, monkeypatch
    ):
        """``KENBOARD_BASE_URL`` overrides even the ``Host`` header."""
        monkeypatch.setattr(Config, "KENBOARD_BASE_URL", "https://board.example")
        mk_user(db, queries, "victim", email="victim@example.org")
        auth_app.test_client().post(
            "/forgot-password",
            data={"email": "victim@example.org"},
            headers={"Host": "evil.example"},
        )
        assert sent_mail["reset_url"].startswith(
            "https://board.example/reset-password/"
        )

    def test_onboarding_runbook_uses_base_url(self, auth_app, monkeypatch):
        """The public runbook advertises the canonical URL when configured."""
        monkeypatch.setattr(Config, "KENBOARD_BASE_URL", "https://board.example")
        resp = auth_app.test_client().get(
            "/onboard/cat/c1/project/p1", headers={"Host": "evil.example"}
        )
        body = resp.get_data(as_text=True)
        assert "base_url=https://board.example" in body
        assert "evil.example" not in body


# -- #1185 — cross-project wiki listings are scope-filtered -------------------


class TestWikiListingScopes:
    """#1185 — ``/wiki/all`` and ``/wiki/unclassified`` honour user scopes."""

    @pytest.fixture
    def boards(self, auth_app, db, queries):
        """Two boards, one classified + one unclassified task each; user sees A."""
        cat_a, cat_b = mk_cat(db, queries, "A"), mk_cat(db, queries, "B")
        proj_a = mk_proj(db, queries, cat_a, "pa")
        proj_b = mk_proj(db, queries, cat_b, "pb")
        for proj, tag in ((proj_a, "A"), (proj_b, "B")):
            tid = mk_task(db, queries, proj, f"classified {tag}")
            queries.wiki_classify(db, task_id=tid, section_path="x", classified_by="q")
            mk_task(db, queries, proj, f"unclassified {tag}")
        uid = mk_user(db, queries, "lowpriv")
        queries.usr_scopes_add(db, user_id=uid, category_id=cat_a, scope="read")
        mk_user(db, queries, "boss", admin=True)
        return {"a": proj_a, "b": proj_b}

    @pytest.mark.usefixtures("boards")
    def test_all_only_returns_readable_projects(self, auth_app):
        """A scoped user gets board A's rows and none of board B's."""
        rows = login(auth_app, "lowpriv").get("/api/v1/wiki/all").get_json()
        assert [r["title"] for r in rows] == ["classified A"]

    @pytest.mark.usefixtures("boards")
    def test_unclassified_only_returns_readable_projects(self, auth_app):
        """Same filter on the unclassified queue."""
        rows = login(auth_app, "lowpriv").get("/api/v1/wiki/unclassified").get_json()
        assert [r["title"] for r in rows] == ["unclassified A"]

    @pytest.mark.usefixtures("boards")
    def test_user_without_scope_gets_nothing(self, auth_app, db, queries):
        """No scope at all → empty listings, not the whole instance."""
        mk_user(db, queries, "nobody")
        client = login(auth_app, "nobody")
        assert client.get("/api/v1/wiki/all").get_json() == []
        assert client.get("/api/v1/wiki/unclassified").get_json() == []

    @pytest.mark.usefixtures("boards")
    def test_admin_still_sees_everything(self, auth_app):
        """Admins keep the unfiltered cross-project view."""
        rows = login(auth_app, "boss").get("/api/v1/wiki/all").get_json()
        assert {r["title"] for r in rows} == {"classified A", "classified B"}


# -- #1187 — a per-project api_key stays inside its project -------------------


class TestApiKeyStaysInScope:
    """#1187 — an api_key cannot write outside the projects it is scoped on."""

    @pytest.fixture
    def two_boards(self, auth_app, db, queries):
        """Projects A and B on two boards; the key is ``write`` on A only."""
        cat_a, cat_b = mk_cat(db, queries, "A"), mk_cat(db, queries, "B")
        proj_a = mk_proj(db, queries, cat_a, "pa")
        proj_b = mk_proj(db, queries, cat_b, "pb")
        headers, key_id = mk_key(db, queries, proj_a, "write")
        return {
            "cat_a": cat_a,
            "cat_b": cat_b,
            "a": proj_a,
            "b": proj_b,
            "headers": headers,
            "key_id": key_id,
            "client": auth_app.test_client(),
        }

    def test_cannot_move_task_into_foreign_project(self, two_boards, db, queries):
        """PATCH ``project_id`` to a project the key has no scope on → 403."""
        tid = mk_task(db, queries, two_boards["a"], "planted")
        resp = two_boards["client"].patch(
            f"/api/v1/tasks/{tid}",
            json={"project_id": two_boards["b"]},
            headers=two_boards["headers"],
        )
        assert resp.status_code == 403
        assert queries.task_get_by_id(db, id=tid)["project_id"] == two_boards["a"]

    def test_can_move_task_between_its_own_projects(self, two_boards, db, queries):
        """A key scoped ``write`` on both projects may still move a task."""
        queries.key_scopes_add(
            db,
            api_key_id=two_boards["key_id"],
            project_id=two_boards["b"],
            scope="write",
        )
        tid = mk_task(db, queries, two_boards["a"], "legit move")
        resp = two_boards["client"].patch(
            f"/api/v1/tasks/{tid}",
            json={"project_id": two_boards["b"]},
            headers=two_boards["headers"],
        )
        assert resp.status_code == 200
        assert resp.get_json()["project_id"] == two_boards["b"]

    def test_read_only_destination_is_not_enough(self, two_boards, db, queries):
        """``read`` on the destination does not allow moving a task into it."""
        queries.key_scopes_add(
            db,
            api_key_id=two_boards["key_id"],
            project_id=two_boards["b"],
            scope="read",
        )
        tid = mk_task(db, queries, two_boards["a"], "x")
        resp = two_boards["client"].patch(
            f"/api/v1/tasks/{tid}",
            json={"project_id": two_boards["b"]},
            headers=two_boards["headers"],
        )
        assert resp.status_code == 403

    def test_cannot_move_project_to_another_category(self, two_boards, db, queries):
        """PATCH ``cat`` on its own project → 403, the project stays put."""
        resp = two_boards["client"].patch(
            f"/api/v1/projects/{two_boards['a']}",
            json={"cat": two_boards["cat_b"]},
            headers=two_boards["headers"],
        )
        assert resp.status_code == 403
        row = queries.proj_get_by_id(db, id=two_boards["a"])
        assert row["cat_id"] == two_boards["cat_a"]

    def test_project_order_ignores_foreign_projects(self, two_boards, db, queries):
        """``project_order`` only repositions projects of the same category."""
        resp = two_boards["client"].patch(
            f"/api/v1/projects/{two_boards['a']}",
            json={"project_order": ["filler", two_boards["b"], two_boards["a"]]},
            headers=two_boards["headers"],
        )
        assert resp.status_code == 200
        assert queries.proj_get_by_id(db, id=two_boards["b"])["position"] == 0
        assert queries.proj_get_by_id(db, id=two_boards["a"])["position"] == 2

    def test_key_still_works_on_its_own_project(self, two_boards, db, queries):
        """Regression guard: ordinary CRUD inside the scoped project is intact."""
        client, headers = two_boards["client"], two_boards["headers"]
        created = client.post(
            "/api/v1/tasks",
            json={"project_id": two_boards["a"], "title": "ok"},
            headers=headers,
        )
        assert created.status_code == 201
        tid = created.get_json()["id"]
        assert client.get(f"/api/v1/tasks/{tid}", headers=headers).status_code == 200
        patched = client.patch(
            f"/api/v1/tasks/{tid}", json={"status": "doing"}, headers=headers
        )
        assert patched.status_code == 200
        assert (
            client.patch(
                f"/api/v1/projects/{two_boards['a']}",
                json={"name": "renamed"},
                headers=headers,
            ).status_code
            == 200
        )
        assert client.delete(f"/api/v1/tasks/{tid}", headers=headers).status_code == 204


# -- #1190 — nothing secret reaches the log file ------------------------------


class TestLogRedaction:
    """#1190 — request bodies and validation errors are logged without secrets."""

    def test_redact_masks_credentials_at_any_depth(self):
        """Keys naming a credential are masked, whatever the nesting."""
        from dashboard.logging import REDACTED, redact

        body = {
            "name": "Q",
            "password": "hunter2-hunter2",
            "nested": [{"new_password": "x", "api_token": "kb_abc", "ok": 1}],
            "key": "kb_plain",
        }
        assert redact(body) == {
            "name": "Q",
            "password": REDACTED,
            "nested": [{"new_password": REDACTED, "api_token": REDACTED, "ok": 1}],
            "key": REDACTED,
        }
        assert body["password"] == "hunter2-hunter2"  # input left untouched

    def test_redact_truncates_long_values(self):
        """A long description / attachement is cut, with its original size noted."""
        from dashboard.logging import MAX_LOGGED_VALUE, redact

        out = redact({"description": "x" * 5000, "n": None})
        assert out["description"].startswith("x" * MAX_LOGGED_VALUE + "…")
        assert "4800 chars" in out["description"]
        assert out["n"] is None

    def test_request_log_never_contains_the_password(
        self, auth_app, db, queries, caplog
    ):
        """End to end: creating a user and changing a password, then grep the log."""
        import logging

        uid = mk_user(db, queries, "boss", admin=True)
        client = login(auth_app, "boss")
        new_pw = "une phrase de passe assez longue 91!"
        with caplog.at_level(logging.DEBUG):
            created = client.post(
                "/api/v1/users",
                json={"name": "n1", "color": "#0969da", "password": new_pw},
                headers=ORIGIN,
            )
            changed = client.post(
                f"/api/v1/users/{uid}/password",
                json={"old_password": PW, "new_password": new_pw + "?"},
                headers=ORIGIN,
            )
        assert (created.status_code, changed.status_code) == (201, 204)
        assert any("/api/v1/users" in r.getMessage() for r in caplog.records)
        for record in caplog.records:
            assert new_pw not in record.getMessage()
            assert PW not in record.getMessage()

    def test_validation_error_log_drops_the_input(self, auth_app, db, queries, caplog):
        """A rejected weak password (pydantic ``input``) is not logged either."""
        import logging

        mk_user(db, queries, "boss", admin=True)
        client = login(auth_app, "boss")
        with caplog.at_level(logging.DEBUG):
            resp = client.post(
                "/api/v1/users",
                json={"color": "#0969da", "password": "weak-secret-pw"},
                headers=ORIGIN,
            )
        assert resp.status_code == 422
        assert any("validation_error" in r.getMessage() for r in caplog.records)
        assert not [r for r in caplog.records if "weak-secret-pw" in r.getMessage()]


# -- #1191 — a password change revokes the other sessions ---------------------


class TestPasswordChangeRevokesSessions:
    """#1191 — cookies issued before a password change stop working."""

    NEW_PW = "une autre phrase tres longue 77?"

    def test_self_service_change_kills_other_sessions_keeps_current(
        self, auth_app, db, queries
    ):
        """The stolen cookie dies; the tab that changed the password stays logged in."""
        uid = mk_user(db, queries, "carol")
        stolen, owner = login(auth_app, "carol"), login(auth_app, "carol")
        resp = owner.post(
            f"/api/v1/users/{uid}/password",
            json={"old_password": PW, "new_password": self.NEW_PW},
            headers=ORIGIN,
        )
        assert resp.status_code == 204
        assert stolen.get("/api/v1/categories").status_code == 401
        assert owner.get("/api/v1/categories").status_code == 200

    def test_admin_reset_kills_every_session_of_the_user(self, auth_app, db, queries):
        """An admin reset logs the target out everywhere — and nobody else."""
        uid = mk_user(db, queries, "carol")
        mk_user(db, queries, "boss", admin=True)
        victim_session, admin = login(auth_app, "carol"), login(auth_app, "boss")
        resp = admin.post(
            f"/api/v1/users/{uid}/reset-password",
            json={"new_password": self.NEW_PW},
            headers=ORIGIN,
        )
        assert resp.status_code == 204
        assert victim_session.get("/api/v1/categories").status_code == 401
        assert admin.get("/api/v1/categories").status_code == 200


# -- #1192 — ``next`` only redirects inside the site --------------------------


class TestLoginRedirect:
    """#1192 — the post-login redirect never leaves the site."""

    @pytest.mark.parametrize(
        "target",
        [
            "/\t/evil.example",
            "/\n/evil.example",
            "/\r/evil.example",
            "/\\evil.example",
            "/ /evil.example",
            "//evil.example",
            "/\x00/evil.example",
            "https://evil.example",
            "javascript:alert(1)",
            "evil.example",
            "",
        ],
    )
    def test_off_site_or_ambiguous_target_falls_back_to_index(
        self, auth_app, db, queries, target
    ):
        """Anything but a clean local path redirects to ``/``."""
        mk_user(db, queries, "bob")
        resp = auth_app.test_client().post(
            "/login", data={"name": "bob", "password": PW, "next": target}
        )
        assert resp.status_code == 302
        assert resp.headers["Location"] == "/"

    @pytest.mark.parametrize("target", ["/cat/abc.html", "/help?x=1&y=2", "/a/b#t-12"])
    def test_local_path_is_followed(self, auth_app, db, queries, target):
        """A local absolute path (query and fragment included) is honoured."""
        mk_user(db, queries, "bob")
        resp = auth_app.test_client().post(
            "/login", data={"name": "bob", "password": PW, "next": target}
        )
        assert resp.headers["Location"] == target


# -- #1193 — api_key lifetime -------------------------------------------------


class TestApiKeyLifetime:
    """#1193 — keys die with their owner; unused onboarding links expire."""

    def test_deleting_a_user_revokes_their_keys(self, auth_app, db, queries):
        """The key of a deleted user answers 401; an unrelated key is untouched."""
        proj = mk_proj(db, queries, mk_cat(db, queries, "A"), "pa")
        uid = mk_user(db, queries, "dave")
        mk_user(db, queries, "boss", admin=True)
        owned, _ = mk_key(db, queries, proj, user_id=uid)
        other, _ = mk_key(db, queries, proj)
        admin = login(auth_app, "boss")
        assert admin.delete(f"/api/v1/users/{uid}", headers=ORIGIN).status_code == 204
        anon = auth_app.test_client()
        url = f"/api/v1/tasks?project={proj}"
        assert anon.get(url, headers=owned).status_code == 401
        assert anon.get(url, headers=other).status_code == 200

    def _onboard(self, auth_app, db, queries):
        """Create an onboarding token as admin; return ``(project id, headers)``."""
        proj = mk_proj(db, queries, mk_cat(db, queries, "A"), "pa")
        mk_user(db, queries, "boss", admin=True)
        resp = login(auth_app, "boss").post(
            "/api/v1/keys/onboard", json={"project_id": proj}, headers=ORIGIN
        )
        assert resp.status_code == 201
        return proj, {"Authorization": f"Bearer {resp.get_json()['key']}"}

    def _onboarding_row(self, db, proj):
        """The api_key row behind the onboarding token of ``proj``."""
        cur = db.cursor()
        cur.execute(
            "SELECT k.key_type, k.expires_at, "
            "TIMESTAMPDIFF(HOUR, NOW(), k.expires_at) AS hours_left "
            "FROM api_keys k JOIN api_key_projects p ON p.api_key_id = k.id "
            "WHERE p.project_id = %s",
            (proj,),
        )
        return cur.fetchone()

    def test_fresh_onboarding_token_has_a_deadline(self, auth_app, db, queries):
        """An onboarding link is born with an expiry a few days out."""
        from dashboard.routes.keys import ONBOARDING_TOKEN_DAYS

        proj, _ = self._onboard(auth_app, db, queries)
        row = self._onboarding_row(db, proj)
        assert row["key_type"] == "onboarding"
        assert ONBOARDING_TOKEN_DAYS * 24 - 1 <= row["hours_left"]
        assert row["hours_left"] <= ONBOARDING_TOKEN_DAYS * 24

    def test_first_use_lifts_the_deadline(self, auth_app, db, queries):
        """Once an agent used the link, the key is permanent (``onboarded``)."""
        proj, headers = self._onboard(auth_app, db, queries)
        resp = auth_app.test_client().get(
            f"/api/v1/tasks?project={proj}", headers=headers
        )
        assert resp.status_code == 200
        row = self._onboarding_row(db, proj)
        assert (row["key_type"], row["expires_at"]) == ("onboarded", None)

    def test_unused_onboarding_token_expires(self, auth_app, db, queries):
        """Past its deadline, a never-used onboarding link is refused."""
        proj, headers = self._onboard(auth_app, db, queries)
        db.cursor().execute(
            "UPDATE api_keys SET expires_at = NOW() - INTERVAL 1 MINUTE"
        )
        resp = auth_app.test_client().get(
            f"/api/v1/tasks?project={proj}", headers=headers
        )
        assert resp.status_code == 401


# -- #1195 — hardening --------------------------------------------------------


class TestHardening:
    """#1195 — defence-in-depth items from the audit."""

    def test_admin_routes_do_not_rely_on_the_middleware_alone(
        self, auth_app, db, queries, monkeypatch
    ):
        """With the middleware's prefix table emptied, the routes still say 403."""
        import dashboard.auth_api_key as auth_api_key

        uid = mk_user(db, queries, "lowpriv")
        client = login(auth_app, "lowpriv")
        monkeypatch.setattr(auth_api_key, "ADMIN_ONLY_PREFIXES", ())
        assert client.get("/api/v1/users").status_code == 403
        assert client.get("/api/v1/keys").status_code == 403
        promote = client.patch(
            f"/api/v1/users/{uid}", json={"is_admin": True}, headers=ORIGIN
        )
        assert promote.status_code == 403
        assert queries.usr_get_by_id(db, id=uid)["is_admin"] == 0
        # The self-service password change stays reachable.
        changed = client.post(
            f"/api/v1/users/{uid}/password",
            json={"old_password": PW, "new_password": "encore une longue phrase 5!"},
            headers=ORIGIN,
        )
        assert changed.status_code == 204

    @pytest.mark.parametrize(
        "payload",
        [
            {"name": "n", "color": "red;background:url(//evil.example)"},
            {"name": "n", "color": "#0969da", "email": "a@evil.com, b@x.org"},
            {"name": "n", "color": "#0969da", "email": "not-an-address"},
        ],
    )
    def test_user_fields_are_validated(self, auth_app, db, queries, payload):
        """A user's color is CSS-safe and their email a single plain address."""
        mk_user(db, queries, "boss", admin=True)
        resp = login(auth_app, "boss").post(
            "/api/v1/users", json=payload, headers=ORIGIN
        )
        assert resp.status_code == 422

    def test_user_update_color_is_validated(self, auth_app, db, queries):
        """Same allowlist on PATCH; a palette value still goes through."""
        uid = mk_user(db, queries, "boss", admin=True)
        client = login(auth_app, "boss")
        url = f"/api/v1/users/{uid}"
        bad = client.patch(url, json={"color": "expression(1)"}, headers=ORIGIN)
        good = client.patch(url, json={"color": "var(--accent)"}, headers=ORIGIN)
        assert (bad.status_code, good.status_code) == (422, 200)

    def test_overlong_who_is_a_422_not_a_500(self, auth_app, db, queries):
        """``who`` longer than its column is rejected at validation time."""
        proj = mk_proj(db, queries, mk_cat(db, queries, "A"), "pa")
        headers, _ = mk_key(db, queries, proj)
        resp = auth_app.test_client().post(
            "/api/v1/tasks",
            json={"project_id": proj, "title": "t", "who": "w" * 101},
            headers=headers,
        )
        assert resp.status_code == 422

    def test_unknown_user_costs_one_hash_verification(self, db, monkeypatch):
        """Login for a non-existent name still runs argon2 (no timing oracle)."""
        import dashboard.auth_login as auth_login

        calls = []
        real_verify = auth_login._hasher.verify

        class Spy:
            def verify(self, hashed, password):
                calls.append(hashed)
                return real_verify(hashed, password)

        monkeypatch.setattr(auth_login, "_hasher", Spy())
        assert auth_login._verify_credentials("ghost", "whatever") is None
        assert calls == [auth_login._DUMMY_HASH]

    def test_oversized_request_is_refused(self, auth_app, db, queries, monkeypatch):
        """A body above ``MAX_CONTENT_LENGTH`` is a 413, never parsed."""
        from dashboard.app import MAX_REQUEST_BYTES

        assert auth_app.config["MAX_CONTENT_LENGTH"] == MAX_REQUEST_BYTES
        monkeypatch.setitem(auth_app.config, "MAX_CONTENT_LENGTH", 1024)
        proj = mk_proj(db, queries, mk_cat(db, queries, "A"), "pa")
        headers, _ = mk_key(db, queries, proj)
        resp = auth_app.test_client().post(
            "/api/v1/tasks",
            json={"project_id": proj, "title": "t", "description": "x" * 4096},
            headers=headers,
        )
        assert resp.status_code == 413

    def test_admin_key_comparison(self, auth_app, db, monkeypatch):
        """The static admin key still works; near-misses and odd bytes do not."""
        monkeypatch.setattr(Config, "KENBOARD_ADMIN_KEY", "kb_admin-secret")
        client = auth_app.test_client()

        def status(token):
            return client.get(
                "/api/v1/users", headers={"Authorization": f"Bearer {token}"}
            ).status_code

        assert status("kb_admin-secret") == 200
        assert status("kb_admin-secre") == 401
        assert status("kb_admin-secreté") == 401
