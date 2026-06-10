"""Unit tests for ``dashboard.email`` — SMTP sending paths (ken #798).

``smtplib.SMTP`` is mocked at the module boundary; the Jinja2 rendering runs for real
against the shipped ``templates/email/*`` files.
"""

from unittest.mock import MagicMock, patch

import pytest

from dashboard import email as email_mod
from dashboard.config import Config

TEMPLATE = "email/password_reset.html"


@pytest.fixture()
def smtp_app(app, monkeypatch):
    """App wired into the email module with SMTP 'configured' (no TLS/auth)."""
    monkeypatch.setattr(Config, "SMTP_ENABLED", True)
    monkeypatch.setattr(Config, "SMTP_HOST", "smtp.test.local")
    monkeypatch.setattr(Config, "SMTP_PORT", 2525)
    monkeypatch.setattr(Config, "SMTP_FROM", "kenboard@test.local")
    monkeypatch.setattr(Config, "SMTP_USE_TLS", False)
    monkeypatch.setattr(Config, "SMTP_USER", "")
    monkeypatch.setattr(Config, "SMTP_PASSWORD", "")
    email_mod.init_email(app)
    return app


class TestSendEmailGuards:
    """Failure guards: misconfiguration never raises, returns False."""

    def test_smtp_disabled_returns_false(self, monkeypatch):
        """No SMTP configured → warn + False, nothing sent."""
        monkeypatch.setattr(Config, "SMTP_ENABLED", False)
        assert email_mod.send_email("a@b.c", "Sujet", TEMPLATE) is False

    def test_uninitialized_app_returns_false(self, monkeypatch):
        """init_email never called → error + False."""
        monkeypatch.setattr(Config, "SMTP_ENABLED", True)
        monkeypatch.setattr(email_mod, "_app", None)
        assert email_mod.send_email("a@b.c", "Sujet", TEMPLATE) is False

    @pytest.mark.usefixtures("smtp_app")
    def test_render_error_returns_false(self):
        """Unknown template → render error is caught, False returned."""
        with patch("dashboard.email.smtplib.SMTP") as mock_smtp:
            ok = email_mod.send_email("a@b.c", "Sujet", "email/nope.html")
        assert ok is False
        mock_smtp.assert_not_called()

    @pytest.mark.usefixtures("smtp_app")
    def test_smtp_error_returns_false(self):
        """SMTP failure during send is caught, False returned."""
        with patch("dashboard.email.smtplib.SMTP") as mock_smtp:
            srv = mock_smtp.return_value.__enter__.return_value
            srv.sendmail.side_effect = OSError("connection lost")
            ok = email_mod.send_email(
                "a@b.c", "Sujet", TEMPLATE, reset_url="http://x/r/t"
            )
        assert ok is False


class TestSendEmailSuccess:
    """Happy paths against the real Jinja2 templates."""

    def _send(self, **config) -> MagicMock:
        """Send a reset email with a mocked SMTP, return the server mock."""
        with patch("dashboard.email.smtplib.SMTP") as mock_smtp:
            srv = mock_smtp.return_value.__enter__.return_value
            ok = email_mod.send_email(
                "user@test.local",
                "Réinitialisation",
                TEMPLATE,
                reset_url="http://kb.test/reset-password/tok",
            )
            assert ok is True
            mock_smtp.assert_called_once_with(Config.SMTP_HOST, Config.SMTP_PORT)
        return srv

    @pytest.mark.usefixtures("smtp_app")
    def test_sends_multipart_text_and_html(self):
        """Both text/plain and text/html parts are attached (RFC 2046 order)."""
        srv = self._send()
        (from_addr, to_addr, payload), _ = srv.sendmail.call_args
        assert from_addr == "kenboard@test.local"
        assert to_addr == "user@test.local"
        assert 'Content-Type: text/plain; charset="utf-8"' in payload
        assert 'Content-Type: text/html; charset="utf-8"' in payload
        assert payload.index("text/plain") < payload.index("text/html")
        assert "Message-ID" in payload
        srv.starttls.assert_not_called()
        srv.login.assert_not_called()

    @pytest.mark.usefixtures("smtp_app")
    def test_tls_and_login_branches(self, monkeypatch):
        """STARTTLS and AUTH are exercised when configured."""
        monkeypatch.setattr(Config, "SMTP_USE_TLS", True)
        monkeypatch.setattr(Config, "SMTP_USER", "ken")
        monkeypatch.setattr(Config, "SMTP_PASSWORD", "s3cret")
        srv = self._send()
        srv.starttls.assert_called_once()
        srv.login.assert_called_once_with("ken", "s3cret")

    @pytest.mark.usefixtures("smtp_app")
    def test_from_without_domain_falls_back(self, monkeypatch):
        """SMTP_FROM without '@' still builds a Message-ID (kenboard domain)."""
        monkeypatch.setattr(Config, "SMTP_FROM", "kenboard-noreply")
        srv = self._send()
        (_, _, payload), _ = srv.sendmail.call_args
        assert "kenboard>" in payload  # Message-ID domain fallback


class TestInitEmail:
    """init_email wires the app and logs the SMTP state."""

    def test_init_stores_app(self, app, monkeypatch):
        """The app reference is stored for later template rendering."""
        monkeypatch.setattr(Config, "SMTP_ENABLED", False)
        email_mod.init_email(app)
        assert email_mod._app is app
