"""Unit tests for the ``ken`` CLI.

These tests do not hit a real network: HTTP is mocked at the
``urllib.request.urlopen`` boundary, and the working directory is swapped
to a tmp_path so ``.ken`` discovery and writes stay isolated.
"""

import json
import os
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from dashboard import ken

# -- Helpers ------------------------------------------------------------------


class _FakeResponse:
    """Minimal stand-in for the urlopen context manager response."""

    def __init__(self, body: bytes):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def read(self):
        return self._body


def _fake_urlopen(responses):
    """Build a urlopen replacement that pops responses in order.

    Each entry in ``responses`` is a tuple ``(expected_method, expected_path,
    response_body)``. ``response_body`` is a python object that will be
    JSON-encoded, or ``None`` for an empty body.
    """
    calls = []
    queue = list(responses)

    def _impl(req, *_args, **_kwargs):
        method = req.get_method()
        url = req.full_url
        body_bytes = req.data
        body_obj = json.loads(body_bytes.decode()) if body_bytes else None
        calls.append((method, url, body_obj, dict(req.headers)))
        if not queue:
            raise AssertionError(f"unexpected call: {method} {url}")
        expected_method, expected_path_substr, payload = queue.pop(0)
        assert method == expected_method, (method, expected_method)
        assert expected_path_substr in url, (url, expected_path_substr)
        return _FakeResponse(b"" if payload is None else json.dumps(payload).encode())

    return _impl, calls


@pytest.fixture()
def cwd_tmp(tmp_path, monkeypatch):
    """Run the test from a clean tmp directory and clear KEN_* env vars."""
    monkeypatch.chdir(tmp_path)
    for key in ("KEN_PROJECT_ID", "KEN_BASE_URL", "KEN_API_TOKEN"):
        monkeypatch.delenv(key, raising=False)
    return tmp_path


@pytest.fixture()
def runner():
    return CliRunner()


# -- Config resolution --------------------------------------------------------


class TestLoadConfig:
    """Resolution priority: flags > env > .ken > defaults."""

    def test_defaults_when_nothing_set(self, cwd_tmp):
        cfg = ken._load_config()
        assert cfg.project_id is None
        assert cfg.base_url == ken.DEFAULT_BASE_URL
        assert cfg.api_token is None
        assert cfg.ken_file is None

    def test_ken_file_in_cwd(self, cwd_tmp):
        (cwd_tmp / ".ken").write_text(
            "project_id=abc\nbase_url=http://x:9090\napi_token=tok123\n"
        )
        os.chmod(cwd_tmp / ".ken", 0o600)
        cfg = ken._load_config()
        assert cfg.project_id == "abc"
        assert cfg.base_url == "http://x:9090"
        assert cfg.api_token == "tok123"
        assert cfg.ken_file == cwd_tmp / ".ken"

    def test_ken_file_walk_up(self, cwd_tmp):
        (cwd_tmp / ".ken").write_text("project_id=root-uuid\n")
        os.chmod(cwd_tmp / ".ken", 0o600)
        sub = cwd_tmp / "deep" / "nested"
        sub.mkdir(parents=True)
        os.chdir(sub)
        cfg = ken._load_config()
        assert cfg.project_id == "root-uuid"

    def test_env_overrides_file(self, cwd_tmp, monkeypatch):
        (cwd_tmp / ".ken").write_text("project_id=from-file\n")
        os.chmod(cwd_tmp / ".ken", 0o600)
        monkeypatch.setenv("KEN_PROJECT_ID", "from-env")
        cfg = ken._load_config()
        assert cfg.project_id == "from-env"

    def test_flag_overrides_env(self, cwd_tmp, monkeypatch):
        monkeypatch.setenv("KEN_PROJECT_ID", "from-env")
        cfg = ken._load_config(project_override="from-flag")
        assert cfg.project_id == "from-flag"

    def test_base_url_trailing_slash_stripped(self, cwd_tmp):
        cfg = ken._load_config(base_url_override="http://x:9090/")
        assert cfg.base_url == "http://x:9090"

    def test_warns_on_loose_permissions(self, cwd_tmp, capsys):
        path = cwd_tmp / ".ken"
        path.write_text("project_id=abc\n")
        os.chmod(path, 0o644)
        ken._load_config()
        assert "mode 644" in capsys.readouterr().err


# -- Format helpers -----------------------------------------------------------


class TestFormatColumns:
    """Aligned column formatter."""

    def test_empty_rows(self):
        assert ken._format_columns([], [("ID", "id")]) == "(no rows)"

    def test_aligns_columns(self):
        rows = [
            {"id": 1, "title": "short"},
            {"id": 100, "title": "longer title"},
        ]
        out = ken._format_columns(rows, [("ID", "id"), ("TITLE", "title")])
        lines = out.splitlines()
        assert lines[0] == "ID   TITLE       "
        assert lines[1] == "1    short       "
        assert lines[2] == "100  longer title"

    def test_none_renders_dash(self):
        out = ken._format_columns(
            [{"id": 1, "who": None}], [("ID", "id"), ("WHO", "who")]
        )
        assert "--" in out


# -- HTTP layer ---------------------------------------------------------------


class TestRequest:
    """The internal _request helper."""

    def test_get_returns_parsed_json(self, cwd_tmp):
        impl, calls = _fake_urlopen([("GET", "/api/v1/projects", [{"id": "p1"}])])
        cfg = ken.KenConfig(
            project_id=None,
            base_url="http://x:9090",
            api_token=None,
            ken_file=None,
        )
        with patch("dashboard.ken.urllib_request.urlopen", impl):
            data = ken._request(cfg, "GET", "/api/v1/projects")
        assert data == [{"id": "p1"}]
        assert calls[0][0] == "GET"
        assert "/api/v1/projects" in calls[0][1]
        assert "Authorization" not in calls[0][3]

    def test_sends_bearer_token_when_set(self, cwd_tmp):
        impl, calls = _fake_urlopen([("GET", "/api/v1/projects", [])])
        cfg = ken.KenConfig(
            project_id=None,
            base_url="http://x:9090",
            api_token="secret123",
            ken_file=None,
        )
        with patch("dashboard.ken.urllib_request.urlopen", impl):
            ken._request(cfg, "GET", "/api/v1/projects")
        assert calls[0][3].get("Authorization") == "Bearer secret123"

    def test_post_sends_body(self, cwd_tmp):
        impl, calls = _fake_urlopen([("POST", "/api/v1/tasks", {"id": 1})])
        cfg = ken.KenConfig(
            project_id="p", base_url="http://x:9090", api_token=None, ken_file=None
        )
        with patch("dashboard.ken.urllib_request.urlopen", impl):
            ken._request(cfg, "POST", "/api/v1/tasks", body={"title": "T"})
        assert calls[0][2] == {"title": "T"}


# -- CLI commands -------------------------------------------------------------


def _patch_responses(responses):
    """Context manager that patches urlopen with the queued responses."""
    impl, calls = _fake_urlopen(responses)
    return patch("dashboard.ken.urllib_request.urlopen", impl), calls


class TestCliInit:
    """`ken init` writes .ken with mode 0600 and updates .gitignore."""

    def test_init_with_uuid(self, cwd_tmp, runner):
        # Make this look like a git repo so .gitignore handling kicks in
        (cwd_tmp / ".git").mkdir()
        ctx, _ = _patch_responses(
            [
                (
                    "GET",
                    "/api/v1/projects",
                    [{"id": "uuid-1", "name": "MyProj", "acronym": "MP"}],
                )
            ]
        )
        with ctx:
            result = runner.invoke(ken.cli, ["init", "uuid-1"])
        assert result.exit_code == 0, result.output
        ken_file = cwd_tmp / ".ken"
        assert ken_file.exists()
        content = ken_file.read_text()
        assert "project_id=uuid-1" in content
        assert "base_url=" in content
        # Mode 0600
        mode = ken_file.stat().st_mode & 0o777
        assert mode == 0o600
        # .gitignore created with .ken
        gi = (cwd_tmp / ".gitignore").read_text()
        assert ".ken" in gi.splitlines()

    def test_init_unknown_uuid_fails(self, cwd_tmp, runner):
        ctx, _ = _patch_responses(
            [("GET", "/api/v1/projects", [{"id": "other", "name": "X"}])]
        )
        with ctx:
            result = runner.invoke(ken.cli, ["init", "missing-uuid"])
        assert result.exit_code != 0
        assert "not found" in result.output

    def test_init_refuses_overwrite(self, cwd_tmp, runner):
        (cwd_tmp / ".ken").write_text("project_id=existing\n")
        os.chmod(cwd_tmp / ".ken", 0o600)
        result = runner.invoke(ken.cli, ["init", "uuid-1"])
        assert result.exit_code != 0
        assert "already exists" in result.output

    def test_init_force_overwrites(self, cwd_tmp, runner):
        (cwd_tmp / ".ken").write_text("project_id=old\n")
        os.chmod(cwd_tmp / ".ken", 0o600)
        ctx, _ = _patch_responses(
            [("GET", "/api/v1/projects", [{"id": "uuid-1", "name": "New"}])]
        )
        with ctx:
            result = runner.invoke(ken.cli, ["init", "uuid-1", "--force"])
        assert result.exit_code == 0, result.output
        assert "project_id=uuid-1" in (cwd_tmp / ".ken").read_text()

    def test_init_appends_to_existing_gitignore(self, cwd_tmp, runner):
        (cwd_tmp / ".git").mkdir()
        (cwd_tmp / ".gitignore").write_text("__pycache__/\n*.log\n")
        ctx, _ = _patch_responses(
            [("GET", "/api/v1/projects", [{"id": "uuid-1", "name": "X"}])]
        )
        with ctx:
            result = runner.invoke(ken.cli, ["init", "uuid-1"])
        assert result.exit_code == 0, result.output
        gi_lines = (cwd_tmp / ".gitignore").read_text().splitlines()
        assert "__pycache__/" in gi_lines
        assert "*.log" in gi_lines
        assert ".ken" in gi_lines

    def test_init_skips_gitignore_outside_git_repo(self, cwd_tmp, runner):
        ctx, _ = _patch_responses(
            [("GET", "/api/v1/projects", [{"id": "uuid-1", "name": "X"}])]
        )
        with ctx:
            result = runner.invoke(ken.cli, ["init", "uuid-1"])
        assert result.exit_code == 0, result.output
        assert "not in a git repository" in result.output
        assert not (cwd_tmp / ".gitignore").exists()


class TestCliList:
    """`ken list` reads tasks for the configured project."""

    def test_no_project_fails(self, cwd_tmp, runner):
        result = runner.invoke(ken.cli, ["list"])
        assert result.exit_code != 0
        assert "no project configured" in result.output

    def test_columns_output(self, cwd_tmp, runner):
        (cwd_tmp / ".ken").write_text("project_id=p1\n")
        os.chmod(cwd_tmp / ".ken", 0o600)
        ctx, _ = _patch_responses(
            [
                (
                    "GET",
                    "/api/v1/tasks?project=p1",
                    [
                        {
                            "id": 1,
                            "status": "todo",
                            "who": "Q",
                            "due_date": None,
                            "title": "First",
                        },
                        {
                            "id": 2,
                            "status": "doing",
                            "who": "Claude",
                            "due_date": "2026-04-15",
                            "title": "Second",
                        },
                    ],
                )
            ]
        )
        with ctx:
            result = runner.invoke(ken.cli, ["list"])
        assert result.exit_code == 0, result.output
        assert "First" in result.output
        assert "Second" in result.output
        assert "ID" in result.output
        assert "STATUS" in result.output

    def test_status_filter(self, cwd_tmp, runner):
        (cwd_tmp / ".ken").write_text("project_id=p1\n")
        os.chmod(cwd_tmp / ".ken", 0o600)
        ctx, _ = _patch_responses(
            [
                (
                    "GET",
                    "/api/v1/tasks?project=p1",
                    [
                        {"id": 1, "status": "todo", "title": "A"},
                        {"id": 2, "status": "doing", "title": "B"},
                    ],
                )
            ]
        )
        with ctx:
            result = runner.invoke(ken.cli, ["list", "--status", "doing"])
        assert result.exit_code == 0
        assert "B" in result.output
        assert "A" not in result.output.split("TITLE")[1]

    def test_json_output(self, cwd_tmp, runner):
        (cwd_tmp / ".ken").write_text("project_id=p1\n")
        os.chmod(cwd_tmp / ".ken", 0o600)
        ctx, _ = _patch_responses(
            [("GET", "/api/v1/tasks?project=p1", [{"id": 1, "title": "T"}])]
        )
        with ctx:
            result = runner.invoke(ken.cli, ["list", "--json"])
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed == [{"id": 1, "title": "T"}]


class TestCliMutations:
    """Add / update / move / done / show."""

    def _setup(self, cwd_tmp):
        (cwd_tmp / ".ken").write_text("project_id=p1\n")
        os.chmod(cwd_tmp / ".ken", 0o600)

    def test_add(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        ctx, calls = _patch_responses(
            [
                (
                    "POST",
                    "/api/v1/tasks",
                    {
                        "id": 42,
                        "title": "T",
                        "status": "todo",
                        "who": "Q",
                        "due_date": None,
                    },
                )
            ]
        )
        with ctx:
            result = runner.invoke(
                ken.cli,
                ["add", "T", "--who", "Q"],
            )
        assert result.exit_code == 0, result.output
        assert calls[0][2]["title"] == "T"
        assert calls[0][2]["who"] == "Q"
        assert calls[0][2]["project_id"] == "p1"
        assert calls[0][2]["status"] == "todo"

    def test_update_only_passed_fields(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        ctx, calls = _patch_responses(
            [
                (
                    "PATCH",
                    "/api/v1/tasks/5",
                    {"id": 5, "title": "New", "status": "todo"},
                )
            ]
        )
        with ctx:
            result = runner.invoke(ken.cli, ["update", "5", "--title", "New"])
        assert result.exit_code == 0, result.output
        assert calls[0][2] == {"title": "New"}

    def test_update_no_fields_fails(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        result = runner.invoke(ken.cli, ["update", "5"])
        assert result.exit_code != 0
        assert "nothing to update" in result.output

    def test_move(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        ctx, calls = _patch_responses(
            [("PATCH", "/api/v1/tasks/5", {"id": 5, "status": "doing"})]
        )
        with ctx:
            result = runner.invoke(ken.cli, ["move", "5", "--to", "doing"])
        assert result.exit_code == 0, result.output
        assert calls[0][2] == {"status": "doing"}
        assert "→ doing" in result.output

    def test_done(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        ctx, calls = _patch_responses(
            [("PATCH", "/api/v1/tasks/5", {"id": 5, "status": "done"})]
        )
        with ctx:
            result = runner.invoke(ken.cli, ["done", "5"])
        assert result.exit_code == 0, result.output
        assert calls[0][2] == {"status": "done"}

    def test_show_not_found(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        ctx, _ = _patch_responses([("GET", "/api/v1/tasks?project=p1", [{"id": 1}])])
        with ctx:
            result = runner.invoke(ken.cli, ["show", "999"])
        assert result.exit_code != 0
        assert "not found" in result.output

    def test_show(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        ctx, _ = _patch_responses(
            [
                (
                    "GET",
                    "/api/v1/tasks?project=p1",
                    [
                        {
                            "id": 7,
                            "status": "todo",
                            "who": "Q",
                            "due_date": "2026-04-15",
                            "title": "Hello",
                            "description": "details",
                        }
                    ],
                )
            ]
        )
        with ctx:
            result = runner.invoke(ken.cli, ["show", "7"])
        assert result.exit_code == 0, result.output
        assert "Hello" in result.output
        assert "2026-04-15" in result.output


class TestCliHelp:
    """`ken help` ships the agent best-practice guide as packaged data (#118)."""

    def test_help_prints_agent_guide(self, runner):
        """`ken help` reads the bundled markdown and echoes it verbatim."""
        result = runner.invoke(ken.cli, ["help"])
        assert result.exit_code == 0, result.output
        # Section headings from agent_guide.md
        assert "kenboard agent guide" in result.output
        assert "The loop" in result.output
        # The four-step workflow markers
        assert "todo → doing → review → done" in result.output
        assert "ken move <id> --to doing" in result.output
        assert "ken move <id> --to review" in result.output
        assert "ken update <id> --desc" in result.output

    def test_help_subcommand_listed_in_main_help(self, runner):
        """`ken --help` advertises the new ``help`` subcommand."""
        result = runner.invoke(ken.cli, ["--help"])
        assert result.exit_code == 0
        assert "help" in result.output
        assert "agent guide" in result.output
