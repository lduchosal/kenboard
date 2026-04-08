"""Test the kenboard admin CLI."""

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
