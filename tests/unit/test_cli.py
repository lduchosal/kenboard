"""Test the kenboard admin CLI."""

import sys
from unittest.mock import patch

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
