"""Test the kenboard admin CLI."""

import sys
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from dashboard.cli import cli


class TestServeDebugGuard:
    """``kenboard serve --debug`` must refuse non-localhost binds."""

    def test_refuses_public_host_with_debug(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["serve", "--host", "0.0.0.0", "--debug"])
        assert result.exit_code == 2
        assert "Refusal" in result.output
        assert "RCE" in result.output

    def test_refuses_external_ip_with_debug(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["serve", "--host", "192.168.1.10", "--debug"])
        assert result.exit_code == 2


class TestServeProdGuard:
    """``kenboard serve`` without ``--debug`` must refuse to start (#129).

    The Werkzeug dev server is single-threaded, unhardened, and prints "This is a
    development server. Do not use it in a production deployment." Refusing without
    --debug forces operators to use gunicorn (per INSTALL.md section 7) and removes the
    temptation to serve real traffic from a dev tool.
    """

    def test_refuses_without_debug_flag(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["serve"])
        assert result.exit_code == 2
        assert "Refusal" in result.output
        assert "gunicorn" in result.output
        assert "kenboard serve --debug" in result.output

    def test_refuses_without_debug_even_on_localhost(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["serve", "--host", "127.0.0.1"])
        assert result.exit_code == 2
        assert "Refusal" in result.output

    def test_refuses_without_debug_with_custom_port(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["serve", "--port", "9090"])
        assert result.exit_code == 2
        assert "Refusal" in result.output


class TestProdCommand:
    """``kenboard prod`` wraps gunicorn for the production WSGI server (#129)."""

    def test_missing_gunicorn_gives_clear_error(self):
        """Without the prod extra, the command exits 2 and tells the user how to fix
        it.
        """
        runner = CliRunner()
        # Force the import inside `prod` to fail by blocking the module
        # in sys.modules. This simulates a kenboard install without the
        # `[prod]` extra.
        with patch.dict(sys.modules, {"gunicorn.app.wsgiapp": None}):
            result = runner.invoke(cli, ["prod"])
        assert result.exit_code == 2
        assert "Refusal" in result.output
        assert "gunicorn is not installed" in result.output
        assert 'pip install "kenboard[prod]"' in result.output

    @pytest.mark.skipif(sys.platform == "win32", reason="gunicorn is Unix-only")
    def test_invokes_gunicorn_with_default_argv(self):
        """With gunicorn installed, WSGIApplication is invoked with the right argv."""
        runner = CliRunner()
        with patch("gunicorn.app.wsgiapp.WSGIApplication") as mock_app:
            mock_app.return_value.run.return_value = None
            result = runner.invoke(cli, ["prod"])
        assert result.exit_code == 0, result.output
        mock_app.assert_called_once()
        # The WSGIApplication reads from sys.argv at construction time;
        # the prod command rewrites sys.argv before calling it.
        assert sys.argv == [
            "gunicorn",
            "--bind",
            "0.0.0.0:8080",
            "--workers",
            "4",
            "dashboard.app:create_app()",
        ]

    @pytest.mark.skipif(sys.platform == "win32", reason="gunicorn is Unix-only")
    def test_passes_custom_bind_and_workers(self):
        runner = CliRunner()
        with patch("gunicorn.app.wsgiapp.WSGIApplication") as mock_app:
            mock_app.return_value.run.return_value = None
            result = runner.invoke(
                cli, ["prod", "--bind", "127.0.0.1:9090", "--workers", "2"]
            )
        assert result.exit_code == 0, result.output
        assert sys.argv == [
            "gunicorn",
            "--bind",
            "127.0.0.1:9090",
            "--workers",
            "2",
            "dashboard.app:create_app()",
        ]


class TestUtf8Encoding:
    """#148: ken and kenboard force UTF-8 on Windows.

    On non-Windows platforms the fix is a no-op (guarded by
    ``sys.platform == "win32"``). These tests verify the reconfigure
    logic works and that UTF-8 output survives a round trip through
    the Click test runner. The real Windows path is exercised by the
    CI ``windows-unit`` job.
    """

    def test_ken_outputs_utf8_characters(self):
        """The ken CLI can print → and accented characters without crash."""
        runner = CliRunner()
        from dashboard.ken import cli as ken_cli

        result = runner.invoke(ken_cli, ["--help"])
        assert result.exit_code == 0

    def test_kenboard_outputs_utf8_characters(self):
        """The kenboard CLI can print UTF-8 without crash."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0

    def test_reconfigure_is_safe_on_utf8_stdout(self):
        """Calling reconfigure(encoding='utf-8') on an already-UTF-8 stream is a no-
        op.
        """
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
            assert sys.stdout.encoding.lower().replace("-", "") == "utf8"

    def test_win32_guard_skips_on_current_platform(self):
        """On non-Windows, the win32 block in ken.py does not execute."""
        # The module-level `if sys.platform == "win32"` should not have
        # called reconfigure on this platform. We just verify the module
        # loaded without error (it did, since we imported it above).
        import dashboard.ken

        assert dashboard.ken is not None
