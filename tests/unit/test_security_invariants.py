"""Static security invariants scanned across ``src/dashboard/``.

These tests read source files as text and assert properties that must hold independently
of runtime behaviour. They act as tripwires when a future refactor reintroduces a
dangerous pattern — the code reviewer is forced to look at the invariant before the test
can be silenced.
"""

from __future__ import annotations

from pathlib import Path

import pytest

SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "dashboard"

# Files that are legitimately allowed to read LOGIN_DISABLED directly.
# Any new entry here is a security review trigger — don't add lightly.
#
# - ``auth_user.py`` defines ``_is_login_disabled()``, the single runtime
#   entry point with the production guard (#199).
# - ``app.py`` adds a startup-time refusal-to-start check, belt + braces
#   on top of the runtime helper: if ``LOGIN_DISABLED`` is already set on
#   the app config at the end of ``create_app`` and ``DEBUG=False``, we
#   raise before serving a single request.
ALLOWED_DIRECT_READERS: frozenset[Path] = frozenset(
    {
        SRC_ROOT / "auth_user.py",
        SRC_ROOT / "app.py",
    }
)


def _iter_source_files() -> list[Path]:
    """Return every ``*.py`` under the package, sorted for stable output."""
    return sorted(SRC_ROOT.rglob("*.py"))


class TestLoginDisabledInvariant:
    """#199: ``LOGIN_DISABLED`` can only be consulted via ``_is_login_disabled``.

    The test bypass is off-by-default and gated by ``Config.DEBUG`` inside
    that helper. If any other module reads the flag directly from
    ``app.config``, a misconfigured production deploy would silently
    disable authentication.
    """

    FORBIDDEN_PATTERN = 'config.get("LOGIN_DISABLED")'

    def test_no_direct_read_outside_helper(self):
        """Any direct ``app.config.get("LOGIN_DISABLED")`` call must live inside
        ``auth_user._is_login_disabled`` so the production guard is always applied.
        """
        offenders: list[str] = []
        for py in _iter_source_files():
            text = py.read_text(encoding="utf-8")
            if self.FORBIDDEN_PATTERN not in text:
                continue
            if py in ALLOWED_DIRECT_READERS:
                continue
            offenders.append(str(py.relative_to(SRC_ROOT)))
        if offenders:
            pytest.fail(
                "The following modules read LOGIN_DISABLED directly, "
                "bypassing the #199 production guard. Replace each read "
                "with `_is_login_disabled()` from dashboard.auth_user:\n  - "
                + "\n  - ".join(offenders)
            )

    def test_helper_is_defined(self):
        """Sanity check: ``_is_login_disabled`` must exist in ``auth_user``
        and actually *read* the flag. Guards against a future refactor
        that strips the helper body down to a no-op ``return False``."""
        auth_user = SRC_ROOT / "auth_user.py"
        text = auth_user.read_text(encoding="utf-8")
        assert "def _is_login_disabled" in text, (
            "auth_user.py no longer defines _is_login_disabled — the #199 "
            "production guard has been removed."
        )
        assert self.FORBIDDEN_PATTERN in text, (
            "auth_user.py defines _is_login_disabled but no longer reads "
            "LOGIN_DISABLED — the helper has become a no-op stub."
        )


class TestLoginDisabledRuntimeGuard:
    """#199 runtime behaviour: ``_is_login_disabled`` refuses prod bypass."""

    def test_helper_raises_when_debug_off_and_flag_on(self, app, monkeypatch):
        """Flip ``Config.DEBUG`` to False and set LOGIN_DISABLED on the app.

        The helper must raise ``RuntimeError`` so the request crashes loud
        instead of silently letting the caller through as if it were a
        unit test.
        """
        from dashboard.auth_user import _is_login_disabled
        from dashboard.config import Config

        monkeypatch.setattr(Config, "DEBUG", False)
        prev_flag = app.config.get("LOGIN_DISABLED", False)
        prev_testing = app.config.get("TESTING", False)
        app.config["LOGIN_DISABLED"] = True
        app.config["TESTING"] = False
        try:
            with app.test_request_context("/api/v1/categories"):
                with pytest.raises(RuntimeError, match="LOGIN_DISABLED"):
                    _is_login_disabled()
        finally:
            app.config["LOGIN_DISABLED"] = prev_flag
            app.config["TESTING"] = prev_testing

    def test_helper_allows_bypass_in_debug_mode(self, app, monkeypatch):
        """With ``DEBUG=True`` the bypass works as intended (tests + dev)."""
        from dashboard.auth_user import _is_login_disabled
        from dashboard.config import Config

        monkeypatch.setattr(Config, "DEBUG", True)
        prev_flag = app.config.get("LOGIN_DISABLED", False)
        app.config["LOGIN_DISABLED"] = True
        try:
            with app.test_request_context("/api/v1/categories"):
                assert _is_login_disabled() is True
        finally:
            app.config["LOGIN_DISABLED"] = prev_flag

    def test_helper_returns_false_when_flag_off(self, app):
        """When the flag is off the helper returns False regardless of DEBUG."""
        from dashboard.auth_user import _is_login_disabled

        prev_flag = app.config.get("LOGIN_DISABLED", False)
        app.config["LOGIN_DISABLED"] = False
        try:
            with app.test_request_context("/api/v1/categories"):
                assert _is_login_disabled() is False
        finally:
            app.config["LOGIN_DISABLED"] = prev_flag


class TestCreateAppStartupGuard:
    """#199 defense-in-depth: ``create_app`` refuses to build a prod app with
    ``LOGIN_DISABLED`` already set on environment config.
    """

    def test_create_app_refuses_login_disabled_without_debug(self, monkeypatch):
        """Simulate a misconfigured prod deploy: DEBUG off but the flag leaks
        into the app config (e.g. via ``FLASK_LOGIN_DISABLED`` env var)."""
        from dashboard import app as app_module

        monkeypatch.setenv("DEBUG", "false")
        # Force the app to start with LOGIN_DISABLED pre-set. We cannot set
        # it via env directly (Flask doesn't auto-map it) so we patch
        # ``Flask`` to inject the value right after instantiation.
        original_flask = app_module.Flask

        class _FlaskWithBadConfig(original_flask):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.config["LOGIN_DISABLED"] = True

        monkeypatch.setattr(app_module, "Flask", _FlaskWithBadConfig)

        with pytest.raises(RuntimeError, match="LOGIN_DISABLED"):
            app_module.create_app()
