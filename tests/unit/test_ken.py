"""Unit tests for the ``ken`` CLI.

These tests do not hit a real network: HTTP is mocked at the ``urllib.request.urlopen``
boundary, and the working directory is swapped to a tmp_path so ``.ken`` discovery and
writes stay isolated.
"""

import json
import os
import re
import sys
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
    response_body)``. ``response_body`` is a python object that will be JSON-encoded, or
    ``None`` for an empty body.
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

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix file permissions")
    def test_warns_on_loose_permissions(self, cwd_tmp, capsys):
        path = cwd_tmp / ".ken"
        path.write_text("project_id=abc\n")
        os.chmod(path, 0o644)
        ken._load_config()
        assert "mode 644" in capsys.readouterr().err

    # #473: architecture path comes from .ken or env, with default fallback.
    def test_architecture_defaults_to_ARCHITECTURE_md(self, cwd_tmp):
        assert ken._load_config().architecture == "ARCHITECTURE.md"

    def test_architecture_from_ken_file(self, cwd_tmp):
        (cwd_tmp / ".ken").write_text(
            "project_id=abc\narchitecture=Doc/Spécifications/Architecture.md\n",
            encoding="utf-8",
        )
        os.chmod(cwd_tmp / ".ken", 0o600)
        cfg = ken._load_config()
        # Accented path must round-trip through UTF-8 parsing.
        assert cfg.architecture == "Doc/Spécifications/Architecture.md"

    def test_architecture_env_overrides_file(self, cwd_tmp, monkeypatch):
        (cwd_tmp / ".ken").write_text("architecture=from-file.md\n")
        os.chmod(cwd_tmp / ".ken", 0o600)
        monkeypatch.setenv("KEN_ARCHITECTURE", "from-env.md")
        assert ken._load_config().architecture == "from-env.md"

    # #479: wiki output dirs are configurable in .ken.
    def test_wiki_dirs_default_when_nothing_set(self, cwd_tmp):
        cfg = ken._load_config()
        assert cfg.wiki_dir == "wiki"
        assert cfg.wiki_html_dir == "wiki-html"

    def test_wiki_dirs_from_ken_file(self, cwd_tmp):
        (cwd_tmp / ".ken").write_text(
            "project_id=p\nwiki_dir=doc/wiki/md\nwiki_html_dir=doc/wiki/html\n"
        )
        os.chmod(cwd_tmp / ".ken", 0o600)
        cfg = ken._load_config()
        assert cfg.wiki_dir == "doc/wiki/md"
        assert cfg.wiki_html_dir == "doc/wiki/html"

    def test_wiki_dirs_env_overrides_file(self, cwd_tmp, monkeypatch):
        (cwd_tmp / ".ken").write_text(
            "wiki_dir=from-file\nwiki_html_dir=from-file-html\n"
        )
        os.chmod(cwd_tmp / ".ken", 0o600)
        monkeypatch.setenv("KEN_WIKI_DIR", "from-env")
        monkeypatch.setenv("KEN_WIKI_HTML_DIR", "from-env-html")
        cfg = ken._load_config()
        assert cfg.wiki_dir == "from-env"
        assert cfg.wiki_html_dir == "from-env-html"


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
        content = ken_file.read_text(encoding="utf-8")
        assert "project_id=uuid-1" in content
        assert "base_url=" in content
        # Mode 0600 (Unix only — Windows doesn't enforce POSIX permissions)
        if sys.platform != "win32":
            mode = ken_file.stat().st_mode & 0o777
            assert mode == 0o600
        # .gitignore created with .ken
        gi = (cwd_tmp / ".gitignore").read_text(encoding="utf-8")
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
        assert "project_id=uuid-1" in (cwd_tmp / ".ken").read_text(encoding="utf-8")

    def test_init_appends_to_existing_gitignore(self, cwd_tmp, runner):
        (cwd_tmp / ".git").mkdir()
        (cwd_tmp / ".gitignore").write_text("__pycache__/\n*.log\n")
        ctx, _ = _patch_responses(
            [("GET", "/api/v1/projects", [{"id": "uuid-1", "name": "X"}])]
        )
        with ctx:
            result = runner.invoke(ken.cli, ["init", "uuid-1"])
        assert result.exit_code == 0, result.output
        gi_lines = (cwd_tmp / ".gitignore").read_text(encoding="utf-8").splitlines()
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

    # #393: agents passing multi-line markdown via ``--desc "line1\nline2"``
    # in a bash double-quoted string store literal backslash-n's. The CLI
    # accepts ``--desc -`` to read the body from stdin instead — a
    # heredoc-friendly path that preserves newlines verbatim.
    def test_add_reads_desc_from_stdin_when_dash(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        ctx, calls = _patch_responses(
            [
                (
                    "POST",
                    "/api/v1/tasks",
                    {"id": 1, "title": "T", "status": "todo"},
                )
            ]
        )
        body = "# Heading\n\nLine one.\n\n- bullet"
        with ctx:
            result = runner.invoke(ken.cli, ["add", "T", "--desc", "-"], input=body)
        assert result.exit_code == 0, result.output
        assert calls[0][2]["description"] == body

    def test_update_reads_desc_from_stdin_when_dash(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        ctx, calls = _patch_responses(
            [
                (
                    "PATCH",
                    "/api/v1/tasks/9",
                    {"id": 9, "title": "X", "status": "todo"},
                )
            ]
        )
        body = "line A\nline B\n"
        with ctx:
            result = runner.invoke(ken.cli, ["update", "9", "--desc", "-"], input=body)
        assert result.exit_code == 0, result.output
        assert calls[0][2] == {"description": body}

    def test_add_literal_desc_passes_through_unchanged(self, cwd_tmp, runner):
        """Non-dash --desc value is not magically transformed (regression guard)."""
        self._setup(cwd_tmp)
        ctx, calls = _patch_responses(
            [("POST", "/api/v1/tasks", {"id": 2, "title": "T", "status": "todo"})]
        )
        with ctx:
            result = runner.invoke(ken.cli, ["add", "T", "--desc", "no-stdin-here"])
        assert result.exit_code == 0, result.output
        assert calls[0][2]["description"] == "no-stdin-here"

    # #393: --desc-file PATH is the recommended idiom for agents to pass
    # multi-line markdown. No shell escaping, works on any agent host
    # that can write a temp file.
    def test_add_reads_desc_from_file(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        body = "# Heading\n\nWith multiple\n\n- bullets"
        body_file = cwd_tmp / "body.md"
        body_file.write_text(body, encoding="utf-8")
        ctx, calls = _patch_responses(
            [("POST", "/api/v1/tasks", {"id": 3, "title": "T", "status": "todo"})]
        )
        with ctx:
            result = runner.invoke(ken.cli, ["add", "T", "--desc-file", str(body_file)])
        assert result.exit_code == 0, result.output
        assert calls[0][2]["description"] == body

    def test_update_reads_desc_from_file(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        body = "line A\nline B\n"
        body_file = cwd_tmp / "update.md"
        body_file.write_text(body, encoding="utf-8")
        ctx, calls = _patch_responses(
            [("PATCH", "/api/v1/tasks/11", {"id": 11, "status": "todo"})]
        )
        with ctx:
            result = runner.invoke(
                ken.cli, ["update", "11", "--desc-file", str(body_file)]
            )
        assert result.exit_code == 0, result.output
        assert calls[0][2] == {"description": body}

    def test_add_with_attachement_file_sends_svg_in_body(self, cwd_tmp, runner):
        """#574: --attachement-file reads the SVG and includes it in the POST."""
        self._setup(cwd_tmp)
        svg = "<svg xmlns='http://www.w3.org/2000/svg'><rect/></svg>"
        path = cwd_tmp / "paint.svg"
        path.write_text(svg, encoding="utf-8")
        ctx, calls = _patch_responses(
            [("POST", "/api/v1/tasks", {"id": 7, "title": "T", "status": "todo"})]
        )
        with ctx:
            result = runner.invoke(
                ken.cli, ["add", "T", "--attachement-file", str(path)]
            )
        assert result.exit_code == 0, result.output
        assert calls[0][2]["attachement"] == svg

    def test_update_with_attachement_file_sends_svg_in_patch(self, cwd_tmp, runner):
        """#574: update --attachement-file writes the SVG into the PATCH body."""
        self._setup(cwd_tmp)
        svg = "<svg xmlns='http://www.w3.org/2000/svg'/>"
        path = cwd_tmp / "p.svg"
        path.write_text(svg, encoding="utf-8")
        ctx, calls = _patch_responses(
            [("PATCH", "/api/v1/tasks/9", {"id": 9, "status": "todo"})]
        )
        with ctx:
            result = runner.invoke(
                ken.cli, ["update", "9", "--attachement-file", str(path)]
            )
        assert result.exit_code == 0, result.output
        assert calls[0][2] == {"attachement": svg}

    def test_attachement_file_too_large_fails_at_cli(self, cwd_tmp, runner):
        """#574: oversized --attachement-file fails on the client, not server."""
        self._setup(cwd_tmp)
        path = cwd_tmp / "huge.svg"
        # Just over the MEDIUMTEXT cap. We monkeypatch the cap to keep
        # the test fast — writing 16 MB to disk would be wasteful.
        path.write_text("x" * 1000, encoding="utf-8")
        import dashboard.ken as ken_mod

        original = ken_mod._ATTACHEMENT_MAX_BYTES
        ken_mod._ATTACHEMENT_MAX_BYTES = 100
        try:
            result = runner.invoke(
                ken.cli, ["add", "T", "--attachement-file", str(path)]
            )
        finally:
            ken_mod._ATTACHEMENT_MAX_BYTES = original
        assert result.exit_code != 0
        assert "too large" in result.output.lower()

    def test_show_displays_attachement_hint(self, cwd_tmp, runner):
        """#574: ken show prints a size hint when the task has an attachement."""
        self._setup(cwd_tmp)
        svg = "<svg/>" * 50
        ctx, _ = _patch_responses(
            [
                (
                    "GET",
                    "/api/v1/tasks?project=p1",
                    [{"id": 42, "title": "T", "status": "todo", "attachement": svg}],
                )
            ]
        )
        with ctx:
            result = runner.invoke(ken.cli, ["show", "42"])
        assert result.exit_code == 0, result.output
        assert "attachement" in result.output
        assert "--save-attachement" in result.output
        # The raw SVG must NOT be printed (would flood the terminal).
        assert svg not in result.output

    def test_polish_writes_desc_and_svg_and_prints_prompt(self, cwd_tmp, runner):
        """#550: ken polish dumps desc + SVG and prints a structured agent prompt."""
        self._setup(cwd_tmp)
        svg = "<svg xmlns='http://www.w3.org/2000/svg'><rect/></svg>"
        ctx, _ = _patch_responses(
            [
                (
                    "GET",
                    "/api/v1/tasks?project=p1",
                    [
                        {
                            "id": 88,
                            "title": "raw paintbrush",
                            "status": "todo",
                            "description": "BLOCKQUOTE text",
                            "attachement": svg,
                        }
                    ],
                )
            ]
        )
        with ctx:
            result = runner.invoke(ken.cli, ["polish", "88", "--tmp-dir", str(cwd_tmp)])
        assert result.exit_code == 0, result.output
        desc_path = cwd_tmp / "kenboard-polish-88.md"
        svg_path = cwd_tmp / "kenboard-polish-88.svg"
        assert desc_path.read_text(encoding="utf-8") == "BLOCKQUOTE text"
        assert svg_path.read_text(encoding="utf-8") == svg
        # The prompt mentions the artefacts + the apply command.
        assert "kenboard-polish-88.md" in result.output
        assert "kenboard-polish-88.svg" in result.output
        assert "ken update 88" in result.output

    def test_polish_without_attachement_skips_svg_file(self, cwd_tmp, runner):
        """#550: ken polish on a task without attachement still works (no SVG)."""
        self._setup(cwd_tmp)
        ctx, _ = _patch_responses(
            [
                (
                    "GET",
                    "/api/v1/tasks?project=p1",
                    [
                        {
                            "id": 9,
                            "title": "plain",
                            "status": "todo",
                            "description": "no SVG here",
                            "attachement": None,
                        }
                    ],
                )
            ]
        )
        with ctx:
            result = runner.invoke(ken.cli, ["polish", "9", "--tmp-dir", str(cwd_tmp)])
        assert result.exit_code == 0, result.output
        assert (cwd_tmp / "kenboard-polish-9.md").exists()
        assert not (cwd_tmp / "kenboard-polish-9.svg").exists()
        assert "(aucun)" in result.output

    def test_show_save_attachement_writes_file(self, cwd_tmp, runner):
        """#574: --save-attachement writes the SVG to disk and skips normal output."""
        self._setup(cwd_tmp)
        svg = "<svg xmlns='http://www.w3.org/2000/svg'><rect/></svg>"
        out = cwd_tmp / "saved.svg"
        ctx, _ = _patch_responses(
            [
                (
                    "GET",
                    "/api/v1/tasks?project=p1",
                    [{"id": 5, "title": "T", "status": "todo", "attachement": svg}],
                )
            ]
        )
        with ctx:
            result = runner.invoke(
                ken.cli, ["show", "5", "--save-attachement", str(out)]
            )
        assert result.exit_code == 0, result.output
        assert out.read_text(encoding="utf-8") == svg

    def test_desc_and_desc_file_are_mutually_exclusive(self, cwd_tmp, runner):
        """Passing both --desc and --desc-file fails with a clear UsageError."""
        self._setup(cwd_tmp)
        body_file = cwd_tmp / "body.md"
        body_file.write_text("x", encoding="utf-8")
        result = runner.invoke(
            ken.cli,
            ["add", "T", "--desc", "literal", "--desc-file", str(body_file)],
        )
        assert result.exit_code != 0
        assert "not both" in result.output.lower()

    def test_desc_file_missing_path_fails(self, cwd_tmp, runner):
        """An unreadable --desc-file path fails fast at the option parser."""
        self._setup(cwd_tmp)
        result = runner.invoke(
            ken.cli, ["add", "T", "--desc-file", str(cwd_tmp / "nope.md")]
        )
        assert result.exit_code != 0

    # #376b: ken wiki groom — agent-driven classification.
    def _write_architecture(self, cwd_tmp, sections_yaml: str) -> str:
        path = cwd_tmp / "ARCHITECTURE.md"
        path.write_text(
            "---\n"
            "wiki:\n"
            "  sections:\n"
            f"{sections_yaml}"
            "---\n\n"
            "# Project architecture\n",
            encoding="utf-8",
        )
        return str(path)

    def test_wiki_groom_no_args_lists_unclassified_and_sections(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        self._write_architecture(
            cwd_tmp,
            "    - id: backend\n"
            "      title: Backend\n"
            "    - id: frontend\n"
            "      title: Frontend\n",
        )
        ctx, _calls = _patch_responses(
            [
                (
                    "GET",
                    "/api/v1/wiki/unclassified",
                    [
                        {
                            "id": 1,
                            "title": "T1",
                            "status": "todo",
                            "who": "Q",
                            "project_id": "p1",
                        }
                    ],
                )
            ]
        )
        with ctx:
            result = runner.invoke(ken.cli, ["wiki", "groom"])
        assert result.exit_code == 0, result.output
        assert "T1" in result.output
        assert "backend" in result.output
        assert "frontend" in result.output

    def test_wiki_groom_classify_validates_section(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        self._write_architecture(
            cwd_tmp,
            "    - id: backend\n      title: Backend\n",
        )
        # POST should NOT happen because validation rejects the section first.
        ctx, calls = _patch_responses([])
        with ctx:
            result = runner.invoke(ken.cli, ["wiki", "groom", "42", "made-up-section"])
        assert result.exit_code != 0
        assert "Unknown section" in result.output
        assert "backend" in result.output  # listed valid paths
        assert calls == []  # no API call

    def test_wiki_groom_classify_happy_path(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        self._write_architecture(
            cwd_tmp,
            "    - id: backend\n      title: Backend\n",
        )
        ctx, calls = _patch_responses(
            [
                (
                    "POST",
                    "/api/v1/wiki/classify",
                    {
                        "task_id": 42,
                        "section_path": "backend",
                        "classified_at": "2026-05-24T12:00:00",
                        "classified_by": "Claude",
                    },
                )
            ]
        )
        with ctx:
            result = runner.invoke(ken.cli, ["wiki", "groom", "42", "backend"])
        assert result.exit_code == 0, result.output
        assert calls[0][2]["task_id"] == 42
        assert calls[0][2]["section_path"] == "backend"

    def test_wiki_groom_show_unclassified_is_friendly(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        # Server returns 404 for unclassified — _request would normally exit
        # the process; the CLI swallows that to print a friendly line.
        import urllib.error as _ue
        from unittest.mock import patch as _patch

        def _raise_404(*_a, **_kw):
            raise _ue.HTTPError(
                "u",
                404,
                "not found",
                {},
                fp=__import__("io").BytesIO(b'{"error":"Unclassified"}'),
            )

        with _patch("dashboard.ken.urllib_request.urlopen", _raise_404):
            result = runner.invoke(ken.cli, ["wiki", "groom", "42", "--show"])
        assert result.exit_code == 0
        assert "unclassified" in result.output.lower()

    def test_wiki_groom_clear_calls_delete(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        ctx, calls = _patch_responses([("DELETE", "/api/v1/wiki/classify/42", None)])
        with ctx:
            result = runner.invoke(ken.cli, ["wiki", "groom", "42", "--clear"])
        assert result.exit_code == 0, result.output
        assert calls[0][0] == "DELETE"
        assert "Cleared" in result.output

    def test_wiki_groom_show_and_clear_mutually_exclusive(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        result = runner.invoke(ken.cli, ["wiki", "groom", "42", "--show", "--clear"])
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output.lower()

    def test_wiki_groom_section_without_task_id_fails(self, cwd_tmp, runner):
        """A non-integer first arg fails at the Click parser level."""
        self._setup(cwd_tmp)
        # Click treats the single arg as TASK_ID; non-int → parser error.
        result = runner.invoke(ken.cli, ["wiki", "groom", "not-an-int"])
        assert result.exit_code != 0

    def test_wiki_groom_help_mentions_karpathy_gist(self, cwd_tmp, runner):
        result = runner.invoke(ken.cli, ["wiki", "groom", "--help"])
        assert result.exit_code == 0
        assert "karpathy" in result.output.lower()
        assert "gist" in result.output.lower()
        assert "LLM Wiki" in result.output

    # #473: --architecture default sourced from .ken `architecture=` key.
    def test_wiki_groom_uses_architecture_path_from_ken_file(self, cwd_tmp, runner):
        (cwd_tmp / ".ken").write_text(
            "project_id=p1\narchitecture=doc/Spécifications/Arch.md\n",
            encoding="utf-8",
        )
        os.chmod(cwd_tmp / ".ken", 0o600)
        # Write the architecture at the custom (accented) path.
        target_dir = cwd_tmp / "doc" / "Spécifications"
        target_dir.mkdir(parents=True)
        (target_dir / "Arch.md").write_text(
            "---\nwiki:\n  sections:\n"
            "    - id: backend\n      title: BackendCustom\n"
            "---\n\n# arch\n",
            encoding="utf-8",
        )
        ctx, _calls = _patch_responses([("GET", "/api/v1/wiki/unclassified", [])])
        with ctx:
            result = runner.invoke(ken.cli, ["wiki", "groom"])
        assert result.exit_code == 0, result.output
        # The section from the *custom* arch path must appear in the listing —
        # proves the default came from .ken, not from ./ARCHITECTURE.md.
        assert "BackendCustom" in result.output

    # #479: wiki sync / wiki build pick the output dir from .ken.
    def test_wiki_sync_writes_to_wiki_dir_from_ken(self, cwd_tmp, runner):
        (cwd_tmp / ".ken").write_text("project_id=p1\nwiki_dir=custom/out\n")
        os.chmod(cwd_tmp / ".ken", 0o600)
        self._write_architecture(cwd_tmp, "    - id: backend\n      title: Backend\n")
        ctx, _calls = _patch_responses([("GET", "/api/v1/wiki/all", [])])
        with ctx:
            result = runner.invoke(ken.cli, ["wiki", "sync"])
        assert result.exit_code == 0, result.output
        # The .ken-configured dir was used, not the ./wiki default.
        assert (cwd_tmp / "custom" / "out" / "index.md").is_file()
        assert not (cwd_tmp / "wiki").exists()

    def test_wiki_build_reads_in_and_writes_out_from_ken(self, cwd_tmp, runner):
        (cwd_tmp / ".ken").write_text(
            "project_id=p1\nwiki_dir=md-src\nwiki_html_dir=html-out\n"
        )
        os.chmod(cwd_tmp / ".ken", 0o600)
        self._write_architecture(cwd_tmp, "    - id: backend\n      title: Backend\n")
        # Pre-stage the MD tree at the configured wiki_dir.
        src = cwd_tmp / "md-src"
        src.mkdir()
        (src / "index.md").write_text("# kenboard wiki\n", encoding="utf-8")
        (src / "backend").mkdir()
        (src / "backend" / "index.md").write_text(
            "# Backend\n\nbody\n", encoding="utf-8"
        )
        result = runner.invoke(ken.cli, ["wiki", "build"])
        assert result.exit_code == 0, result.output
        # HTML landed in the .ken-configured wiki_html_dir, not ./wiki-html.
        assert (cwd_tmp / "html-out" / "backend" / "index.html").is_file()
        assert not (cwd_tmp / "wiki-html").exists()

    def test_wiki_sync_cli_flag_overrides_ken_wiki_dir(self, cwd_tmp, runner):
        (cwd_tmp / ".ken").write_text("project_id=p1\nwiki_dir=from-ken\n")
        os.chmod(cwd_tmp / ".ken", 0o600)
        self._write_architecture(cwd_tmp, "    - id: backend\n      title: Backend\n")
        ctx, _calls = _patch_responses([("GET", "/api/v1/wiki/all", [])])
        with ctx:
            result = runner.invoke(ken.cli, ["wiki", "sync", "--out", "from-flag"])
        assert result.exit_code == 0, result.output
        assert (cwd_tmp / "from-flag" / "index.md").is_file()
        assert not (cwd_tmp / "from-ken").exists()

    def test_wiki_groom_cli_flag_overrides_ken_architecture(self, cwd_tmp, runner):
        (cwd_tmp / ".ken").write_text("project_id=p1\narchitecture=from-ken.md\n")
        os.chmod(cwd_tmp / ".ken", 0o600)
        # Only write the arch at the path passed via --architecture.
        (cwd_tmp / "override.md").write_text(
            "---\nwiki:\n  sections:\n"
            "    - id: ops\n      title: OpsOverride\n"
            "---\n\n# o\n",
            encoding="utf-8",
        )
        ctx, _calls = _patch_responses([("GET", "/api/v1/wiki/unclassified", [])])
        with ctx:
            result = runner.invoke(
                ken.cli, ["wiki", "groom", "--architecture", "override.md"]
            )
        assert result.exit_code == 0, result.output
        assert "OpsOverride" in result.output

    def test_wiki_groom_no_architecture_warns(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        # No ARCHITECTURE.md in cwd_tmp.
        ctx, _calls = _patch_responses([("GET", "/api/v1/wiki/unclassified", [])])
        with ctx:
            result = runner.invoke(ken.cli, ["wiki", "groom"])
        assert result.exit_code == 0
        assert "ARCHITECTURE" in result.output

    # #472: missing ARCHITECTURE.md must surface a clear how-to-fix message.
    def test_wiki_groom_missing_architecture_shows_creation_guide(
        self, cwd_tmp, runner
    ):
        self._setup(cwd_tmp)
        ctx, _calls = _patch_responses([("GET", "/api/v1/wiki/unclassified", [])])
        with ctx:
            result = runner.invoke(ken.cli, ["wiki", "groom"])
        assert result.exit_code == 0
        # The help message must (a) say the file is missing, (b) show the
        # YAML frontmatter to copy-paste, (c) mention the .ken alternative.
        assert "not found" in result.output
        assert "wiki:" in result.output
        assert "sections:" in result.output
        assert "architecture=" in result.output

    def test_wiki_sync_missing_architecture_shows_creation_guide(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        result = runner.invoke(ken.cli, ["wiki", "sync"])
        assert result.exit_code != 0
        assert "not found" in result.output
        assert "architecture=" in result.output

    def test_wiki_sync_empty_sections_shows_distinct_message(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        # File exists but has no wiki.sections block.
        (cwd_tmp / "ARCHITECTURE.md").write_text(
            "---\nfoo: bar\n---\n# arch\n", encoding="utf-8"
        )
        result = runner.invoke(ken.cli, ["wiki", "sync"])
        assert result.exit_code != 0
        # Distinct wording: file exists but no sections block.
        assert "exists but declares no wiki sections" in result.output
        # Still show the YAML example so the operator can fix in-place.
        assert "wiki:" in result.output

    # #376c: ken wiki sync — materialise the MD tree from classifications.
    def test_wiki_sync_writes_tree(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        self._write_architecture(
            cwd_tmp,
            "    - id: backend\n"
            "      title: Backend\n"
            "      sub:\n"
            "        - id: api\n"
            "          title: REST API\n"
            "    - id: frontend\n"
            "      title: Frontend\n",
        )
        rows = [
            {
                "task_id": 1,
                "section_path": "backend/api",
                "classified_at": "2026-05-24T10:00:00",
                "classified_by": "Q",
                "title": "T1",
                "description": "",
                "status": "todo",
                "who": "Q",
                "project_id": "p1",
            },
            {
                "task_id": 2,
                "section_path": "frontend",
                "classified_at": "2026-05-24T11:00:00",
                "classified_by": "Q",
                "title": "T2",
                "description": "",
                "status": "done",
                "who": "Claude",
                "project_id": "p1",
            },
        ]
        ctx, _calls = _patch_responses([("GET", "/api/v1/wiki/all", rows)])
        with ctx:
            result = runner.invoke(ken.cli, ["wiki", "sync"])
        assert result.exit_code == 0, result.output
        wiki = cwd_tmp / "wiki"
        assert (wiki / "index.md").is_file()
        assert (wiki / "backend" / "index.md").is_file()
        assert (wiki / "backend" / "api" / "index.md").is_file()
        assert (wiki / "frontend" / "index.md").is_file()
        assert (wiki / "log.md").is_file()
        # Task assigned to its section
        backend_api = (wiki / "backend" / "api" / "index.md").read_text(
            encoding="utf-8"
        )
        assert "T1" in backend_api
        # Empty section has its index but flagged
        backend_root = (wiki / "backend" / "index.md").read_text(encoding="utf-8")
        assert "no tasks classified yet" in backend_root

    def test_wiki_sync_log_is_desc_by_classified_at(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        self._write_architecture(
            cwd_tmp,
            "    - id: backend\n      title: Backend\n",
        )
        rows = [
            {
                "task_id": 1,
                "section_path": "backend",
                "classified_at": "2026-01-01T00:00:00",
                "classified_by": "old",
                "title": "older",
                "description": "",
                "status": "done",
                "who": "Q",
                "project_id": "p1",
            },
            {
                "task_id": 2,
                "section_path": "backend",
                "classified_at": "2026-06-01T00:00:00",
                "classified_by": "new",
                "title": "newer",
                "description": "",
                "status": "todo",
                "who": "Q",
                "project_id": "p1",
            },
        ]
        ctx, _calls = _patch_responses([("GET", "/api/v1/wiki/all", rows)])
        with ctx:
            result = runner.invoke(ken.cli, ["wiki", "sync"])
        assert result.exit_code == 0, result.output
        log = (cwd_tmp / "wiki" / "log.md").read_text(encoding="utf-8")
        # Newest first → "newer" appears before "older"
        assert log.index("newer") < log.index("older")

    def test_wiki_sync_json_mode_does_not_write(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        self._write_architecture(
            cwd_tmp,
            "    - id: backend\n      title: Backend\n",
        )
        ctx, _calls = _patch_responses([("GET", "/api/v1/wiki/all", [])])
        with ctx:
            result = runner.invoke(ken.cli, ["wiki", "sync", "--json"])
        assert result.exit_code == 0, result.output
        assert not (cwd_tmp / "wiki").exists()
        payload = json.loads(result.output)
        assert "files" in payload
        assert payload["sections"] == 1

    def test_wiki_sync_no_architecture_fails(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        # No ARCHITECTURE.md — must refuse with a usable error.
        result = runner.invoke(ken.cli, ["wiki", "sync"])
        assert result.exit_code != 0
        assert "ARCHITECTURE" in result.output

    def test_wiki_sync_flags_orphans(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        self._write_architecture(
            cwd_tmp,
            "    - id: backend\n      title: Backend\n",
        )
        rows = [
            {
                "task_id": 5,
                "section_path": "removed/section",  # not declared anymore
                "classified_at": "2026-05-24T10:00:00",
                "classified_by": "Q",
                "title": "stale",
                "description": "",
                "status": "todo",
                "who": "Q",
                "project_id": "p1",
            },
        ]
        ctx, _calls = _patch_responses([("GET", "/api/v1/wiki/all", rows)])
        with ctx:
            result = runner.invoke(ken.cli, ["wiki", "sync"])
        assert result.exit_code == 0, result.output
        orphans = (cwd_tmp / "wiki" / "orphans.md").read_text(encoding="utf-8")
        assert "removed/section" in orphans
        assert "stale" in orphans

    # #376d: ken wiki build — render MD tree as standalone HTML.
    def _make_md_tree(self, cwd_tmp):
        """Materialise a minimal wiki/ tree (root + one section + log)."""
        wiki = cwd_tmp / "wiki"
        wiki.mkdir()
        (wiki / "index.md").write_text(
            "# kenboard wiki\n\n- [Backend](backend/index.md) — 1 task\n",
            encoding="utf-8",
        )
        (wiki / "backend").mkdir()
        (wiki / "backend" / "index.md").write_text(
            "# Backend\n\nServer-side.\n\n## Tasks (1)\n\n- **#1** T1 — _todo_ — Q\n",
            encoding="utf-8",
        )
        (wiki / "log.md").write_text(
            "# Classification log\n\n- 2026-05-24 — task #1 → `backend`\n",
            encoding="utf-8",
        )
        return wiki

    def test_wiki_build_renders_html_tree(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        self._write_architecture(
            cwd_tmp,
            "    - id: backend\n      title: Backend\n",
        )
        self._make_md_tree(cwd_tmp)
        result = runner.invoke(ken.cli, ["wiki", "build"])
        assert result.exit_code == 0, result.output
        out = cwd_tmp / "wiki-html"
        assert (out / "index.html").is_file()
        assert (out / "backend" / "index.html").is_file()
        assert (out / "log.html").is_file()
        body = (out / "backend" / "index.html").read_text(encoding="utf-8")
        assert "<h1>Backend</h1>" in body
        # Sidebar nav is present on every page
        assert 'class="sidebar"' in body
        # Inline CSS — page is self-contained
        assert "<style>" in body

    def test_wiki_build_rewrites_md_links_to_html(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        self._write_architecture(
            cwd_tmp,
            "    - id: backend\n      title: Backend\n",
        )
        self._make_md_tree(cwd_tmp)
        runner.invoke(ken.cli, ["wiki", "build"])
        index = (cwd_tmp / "wiki-html" / "index.html").read_text(encoding="utf-8")
        assert 'href="backend/index.html"' in index
        assert "index.md" not in index  # all .md links rewritten

    def test_wiki_build_missing_input_fails(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        self._write_architecture(
            cwd_tmp,
            "    - id: backend\n      title: Backend\n",
        )
        # No wiki/ dir → must refuse with a usable error.
        result = runner.invoke(ken.cli, ["wiki", "build"])
        assert result.exit_code != 0
        assert "does not exist" in result.output

    def test_wiki_build_overwrites_previous_run(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        self._write_architecture(
            cwd_tmp,
            "    - id: backend\n      title: Backend\n",
        )
        self._make_md_tree(cwd_tmp)
        out = cwd_tmp / "wiki-html"
        out.mkdir()
        (out / "stale.html").write_text("garbage")
        runner.invoke(ken.cli, ["wiki", "build"])
        assert not (out / "stale.html").exists()
        assert (out / "index.html").is_file()

    # #376f: per-task detail pages.
    def test_wiki_sync_emits_per_task_detail_pages(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        self._write_architecture(
            cwd_tmp,
            "    - id: backend\n      title: Backend\n",
        )
        rows = [
            {
                "task_id": 42,
                "section_path": "backend",
                "classified_at": "2026-05-24T10:00:00",
                "classified_by": "Claude",
                "title": "AUTH / Login OIDC",
                "description": "## Sub-heading\n\nReally important task body.\n",
                "status": "doing",
                "who": "Claude",
                "project_id": "p1",
            },
        ]
        ctx, _calls = _patch_responses([("GET", "/api/v1/wiki/all", rows)])
        with ctx:
            result = runner.invoke(ken.cli, ["wiki", "sync"])
        assert result.exit_code == 0, result.output
        # Detail page slug = slugified-title + -id.
        detail = cwd_tmp / "wiki" / "backend" / "auth-login-oidc-42.md"
        assert detail.is_file()
        body = detail.read_text(encoding="utf-8")
        assert body.startswith("---")  # YAML frontmatter
        assert "id: 42" in body
        assert "status: doing" in body
        assert "Really important task body" in body
        # Section index links to the detail page (not just the title text).
        index = (cwd_tmp / "wiki" / "backend" / "index.md").read_text(encoding="utf-8")
        assert "[AUTH / Login OIDC](auth-login-oidc-42.md)" in index

    def test_wiki_sync_section_index_splits_active_and_archived(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        self._write_architecture(
            cwd_tmp,
            "    - id: backend\n      title: Backend\n",
        )
        rows = [
            {
                "task_id": 1,
                "section_path": "backend",
                "classified_at": "2026-05-24T10:00:00",
                "classified_by": "Q",
                "title": "Active",
                "description": "",
                "status": "todo",
                "who": "Q",
                "project_id": "p1",
            },
            {
                "task_id": 2,
                "section_path": "backend",
                "classified_at": "2026-05-24T10:00:00",
                "classified_by": "Q",
                "title": "Done",
                "description": "",
                "status": "done",
                "who": "Q",
                "project_id": "p1",
            },
        ]
        ctx, _calls = _patch_responses([("GET", "/api/v1/wiki/all", rows)])
        with ctx:
            runner.invoke(ken.cli, ["wiki", "sync"])
        index = (cwd_tmp / "wiki" / "backend" / "index.md").read_text(encoding="utf-8")
        assert "## En cours (1)" in index
        assert "## Archivé (1)" in index
        # `who` is not in the section index (Q2 decision).
        assert " — Q" not in index
        # Status badge shown only for non-done rows.
        active_pos = index.index("Active")
        done_pos = index.index("Done")
        # "_todo_" appears in the En cours block (before the Archivé block).
        assert "_todo_" in index
        assert index.index("_todo_") < done_pos
        # No _done_ badge in the Archivé block.
        assert "_done_" not in index[active_pos:]

    def test_wiki_sync_slug_collision_resolved_by_id_suffix(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        self._write_architecture(
            cwd_tmp,
            "    - id: ops\n      title: Ops\n",
        )
        rows = [
            {
                "task_id": 10,
                "section_path": "ops",
                "classified_at": "2026-05-24T10:00:00",
                "classified_by": "Q",
                "title": "PYPI / Quality and publish",
                "description": "first",
                "status": "done",
                "who": "Claude",
                "project_id": "p1",
            },
            {
                "task_id": 20,
                "section_path": "ops",
                "classified_at": "2026-05-24T11:00:00",
                "classified_by": "Q",
                "title": "PYPI / Quality and publish",  # same title
                "description": "second",
                "status": "done",
                "who": "Claude",
                "project_id": "p1",
            },
        ]
        ctx, _calls = _patch_responses([("GET", "/api/v1/wiki/all", rows)])
        with ctx:
            runner.invoke(ken.cli, ["wiki", "sync"])
        ops = cwd_tmp / "wiki" / "ops"
        assert (ops / "pypi-quality-and-publish-10.md").is_file()
        assert (ops / "pypi-quality-and-publish-20.md").is_file()

    def test_wiki_build_renders_detail_with_fullscreen_layout(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        self._write_architecture(
            cwd_tmp,
            "    - id: backend\n      title: Backend\n",
        )
        # Sync first, then build.
        rows = [
            {
                "task_id": 7,
                "section_path": "backend",
                "classified_at": "2026-05-24T10:00:00",
                "classified_by": "Claude",
                "title": "Hello world",
                "description": "Body text.",
                "status": "todo",
                "who": "Claude",
                "project_id": "p1",
            },
        ]
        ctx, _calls = _patch_responses([("GET", "/api/v1/wiki/all", rows)])
        with ctx:
            runner.invoke(ken.cli, ["wiki", "sync"])
        runner.invoke(ken.cli, ["wiki", "build"])
        detail = (cwd_tmp / "wiki-html" / "backend" / "hello-world-7.html").read_text(
            encoding="utf-8"
        )
        assert 'class="fullscreen-card"' in detail
        assert 'class="fullscreen-title"' in detail
        assert ">Hello world<" in detail
        assert "status-todo" in detail
        # YAML frontmatter must NOT bleed into the rendered HTML.
        assert "classified_by:" not in detail
        # Footer nav present.
        assert "← retour à backend" in detail
        assert "voir log" in detail

    # #376e: ken wiki lint — orphans / unclassified / empty-section checks.
    def _seed_lint_arch(self, cwd_tmp):
        self._write_architecture(
            cwd_tmp,
            "    - id: backend\n      title: Backend\n"
            "    - id: frontend\n      title: Frontend\n",
        )

    def test_wiki_lint_clean_exits_zero(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        self._seed_lint_arch(cwd_tmp)
        classified = [
            {
                "task_id": 1,
                "section_path": "backend",
                "classified_at": "2026-05-24T10:00:00",
                "classified_by": "Q",
                "title": "T1",
                "description": "",
                "status": "doing",
                "who": "Q",
                "project_id": "p1",
            },
            {
                "task_id": 2,
                "section_path": "frontend",
                "classified_at": "2026-05-24T10:00:00",
                "classified_by": "Q",
                "title": "T2",
                "description": "",
                "status": "todo",
                "who": "Q",
                "project_id": "p1",
            },
        ]
        ctx, _calls = _patch_responses(
            [
                ("GET", "/api/v1/wiki/all", classified),
                ("GET", "/api/v1/wiki/unclassified", []),
            ]
        )
        with ctx:
            result = runner.invoke(ken.cli, ["wiki", "lint"])
        assert result.exit_code == 0, result.output
        assert "0 error(s), 0 warning(s), 0 info" in result.output

    def test_wiki_lint_orphan_is_error_exit_one(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        self._seed_lint_arch(cwd_tmp)
        classified = [
            {
                "task_id": 1,
                "section_path": "removed/section",  # not declared
                "classified_at": "2026-05-24T10:00:00",
                "classified_by": "Q",
                "title": "stale",
                "description": "",
                "status": "done",
                "who": "Q",
                "project_id": "p1",
            },
        ]
        ctx, _calls = _patch_responses(
            [
                ("GET", "/api/v1/wiki/all", classified),
                ("GET", "/api/v1/wiki/unclassified", []),
            ]
        )
        with ctx:
            result = runner.invoke(ken.cli, ["wiki", "lint"])
        assert result.exit_code == 1
        assert "ORPHAN" in result.output
        assert "removed/section" in result.output

    def test_wiki_lint_unclassified_is_warn_default_exit_zero(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        self._seed_lint_arch(cwd_tmp)
        ctx, _calls = _patch_responses(
            [
                (
                    "GET",
                    "/api/v1/wiki/all",
                    [
                        {
                            "task_id": 1,
                            "section_path": "backend",
                            "classified_at": "2026-05-24T10:00:00",
                            "classified_by": "Q",
                            "title": "ok",
                            "description": "",
                            "status": "done",
                            "who": "Q",
                            "project_id": "p1",
                        },
                    ],
                ),
                (
                    "GET",
                    "/api/v1/wiki/unclassified",
                    [
                        {"id": 9, "title": "lone", "status": "todo", "who": "Q"},
                    ],
                ),
            ]
        )
        with ctx:
            result = runner.invoke(ken.cli, ["wiki", "lint"])
        assert result.exit_code == 0
        assert "UNCLASSIFIED" in result.output
        assert "#9" in result.output

    def test_wiki_lint_strict_fails_on_warnings(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        self._seed_lint_arch(cwd_tmp)
        ctx, _calls = _patch_responses(
            [
                ("GET", "/api/v1/wiki/all", []),
                (
                    "GET",
                    "/api/v1/wiki/unclassified",
                    [
                        {"id": 9, "title": "lone", "status": "todo", "who": "Q"},
                    ],
                ),
            ]
        )
        with ctx:
            result = runner.invoke(ken.cli, ["wiki", "lint", "--strict"])
        assert result.exit_code == 1

    def test_wiki_lint_empty_section_is_info_not_failing(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        self._seed_lint_arch(cwd_tmp)
        # ``backend`` declared but no tasks classified there → INFO only.
        classified = [
            {
                "task_id": 1,
                "section_path": "frontend",
                "classified_at": "2026-05-24T10:00:00",
                "classified_by": "Q",
                "title": "ok",
                "description": "",
                "status": "doing",
                "who": "Q",
                "project_id": "p1",
            },
        ]
        ctx, _calls = _patch_responses(
            [
                ("GET", "/api/v1/wiki/all", classified),
                ("GET", "/api/v1/wiki/unclassified", []),
            ]
        )
        with ctx:
            result = runner.invoke(ken.cli, ["wiki", "lint"])
        # Empty section is INFO only — should NOT fail even in --strict.
        assert result.exit_code == 0
        assert "EMPTY-SECTION" in result.output
        assert "backend" in result.output

    def test_wiki_lint_json_mode_emits_stable_schema(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        self._seed_lint_arch(cwd_tmp)
        ctx, _calls = _patch_responses(
            [
                ("GET", "/api/v1/wiki/all", []),
                ("GET", "/api/v1/wiki/unclassified", []),
            ]
        )
        with ctx:
            result = runner.invoke(ken.cli, ["wiki", "lint", "--json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert set(payload.keys()) == {"errors", "warnings", "info", "summary"}
        assert set(payload["summary"].keys()) == {
            "errors",
            "warnings",
            "info",
            "sections",
            "classified",
        }

    def test_wiki_sync_overwrites_previous_run(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        self._write_architecture(
            cwd_tmp,
            "    - id: backend\n      title: Backend\n",
        )
        # Pre-existing stale file in the output dir → must be wiped on next run.
        (cwd_tmp / "wiki").mkdir()
        (cwd_tmp / "wiki" / "stale-from-old-run.md").write_text("garbage")
        ctx, _calls = _patch_responses([("GET", "/api/v1/wiki/all", [])])
        with ctx:
            result = runner.invoke(ken.cli, ["wiki", "sync"])
        assert result.exit_code == 0, result.output
        assert not (cwd_tmp / "wiki" / "stale-from-old-run.md").exists()
        assert (cwd_tmp / "wiki" / "index.md").is_file()

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
        # No grooming reminder when moving to non-review status (#376).
        assert "ken wiki groom" not in result.stderr
        # No résolution reminder either (#605).
        assert "Résolution" not in result.stderr

    def test_move_to_review_prints_groom_reminder(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        ctx, _calls = _patch_responses(
            [("PATCH", "/api/v1/tasks/5", {"id": 5, "status": "review"})]
        )
        with ctx:
            result = runner.invoke(ken.cli, ["move", "5", "--to", "review"])
        assert result.exit_code == 0, result.output
        # Click 8.4 always splits stdout/stderr; reminder is on stderr.
        assert "ken wiki groom 5" in result.stderr
        assert "→ review" in result.stdout

    def test_move_to_review_prints_update_reminder(self, cwd_tmp, runner):
        """`ken move --to review` reminds the agent to log the implementation trail
        (#605).
        """
        self._setup(cwd_tmp)
        ctx, _calls = _patch_responses(
            [("PATCH", "/api/v1/tasks/5", {"id": 5, "status": "review"})]
        )
        with ctx:
            result = runner.invoke(ken.cli, ["move", "5", "--to", "review"])
        assert result.exit_code == 0, result.output
        assert "ken update 5 --desc" in result.stderr
        assert "Résolution" in result.stderr
        assert "Keep the original description intact" in result.stderr

    def test_update_status_review_prints_groom_reminder(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        ctx, _calls = _patch_responses(
            [("PATCH", "/api/v1/tasks/9", {"id": 9, "status": "review"})]
        )
        with ctx:
            result = runner.invoke(ken.cli, ["update", "9", "--status", "review"])
        assert result.exit_code == 0, result.output
        assert "ken wiki groom 9" in result.stderr

    def test_update_status_review_prints_update_reminder(self, cwd_tmp, runner):
        """`ken update --status review` also nudges the agent for the résolution trail
        (#605).
        """
        self._setup(cwd_tmp)
        ctx, _calls = _patch_responses(
            [("PATCH", "/api/v1/tasks/9", {"id": 9, "status": "review"})]
        )
        with ctx:
            result = runner.invoke(ken.cli, ["update", "9", "--status", "review"])
        assert result.exit_code == 0, result.output
        assert "ken update 9 --desc" in result.stderr
        assert "Résolution" in result.stderr

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


class TestSyncHelpers:
    """Pure helpers used by ``ken sync``."""

    def test_sanitize_strips_invalid_chars(self):
        out = ken._sanitize_filename('a/b\\c:d*e?f"g<h>i|j')
        assert "/" not in out
        assert "\\" not in out
        assert ":" not in out
        assert "*" not in out

    def test_sanitize_collapses_whitespace(self):
        assert ken._sanitize_filename("  hello   world  ") == "hello world"

    def test_sanitize_trims_trailing_dots_and_spaces(self):
        assert ken._sanitize_filename("hello...   ") == "hello"

    def test_sanitize_falls_back_to_untitled(self):
        assert ken._sanitize_filename("") == "untitled"
        assert ken._sanitize_filename("   ") == "untitled"
        assert ken._sanitize_filename("...") == "untitled"

    def test_sync_filename_zero_pads_id(self):
        assert ken._sync_filename({"id": 7, "title": "Hi"}) == "0007 - Hi.md"

    def test_sync_filename_uses_sanitized_title(self):
        assert (
            ken._sync_filename({"id": 42, "title": "AGENT / CLI / Foo"})
            == "0042 - AGENT _ CLI _ Foo.md"
        )

    def test_format_markdown_includes_frontmatter_and_body(self):
        out = ken._format_sync_markdown(
            {
                "id": 1,
                "status": "todo",
                "who": "Claude",
                "due_date": None,
                "position": 0,
                "created_at": "2026-04-09T15:00:00",
                "updated_at": "2026-04-09T15:30:00",
                "title": "Hello",
                "description": "body text",
            }
        )
        assert out.startswith("---\n")
        assert "id: 1" in out
        assert "status: todo" in out
        assert "due_date: \n" in out  # None → empty
        assert "# Hello" in out
        assert "body text" in out

    def test_resolve_sync_dir_relative_to_ken(self, tmp_path):
        (tmp_path / ".ken").write_text("project_id=p\n")
        cfg = ken.KenConfig(
            project_id="p",
            base_url="http://x",
            api_token=None,
            ken_file=tmp_path / ".ken",
            sync_dir="doc/kenboard",
        )
        assert ken._resolve_sync_dir(cfg) == tmp_path / "doc" / "kenboard"

    def test_resolve_sync_dir_absolute_kept_as_is(self, tmp_path):
        absolute = tmp_path / "abs"
        cfg = ken.KenConfig(
            project_id="p",
            base_url="http://x",
            api_token=None,
            ken_file=tmp_path / ".ken",
            sync_dir=str(absolute),
        )
        assert ken._resolve_sync_dir(cfg) == absolute


class TestSlugify:
    """``_slugify`` builds the filename portion of wiki task detail pages."""

    def test_basic_lowercase_and_dashes(self):
        assert ken._slugify("Hello World") == "hello-world"

    def test_collapses_runs_of_non_alphanumerics(self):
        assert ken._slugify("foo / bar // baz") == "foo-bar-baz"

    def test_strips_leading_and_trailing_dashes(self):
        assert ken._slugify("  hello  ") == "hello"

    def test_empty_falls_back_to_untitled(self):
        assert ken._slugify("") == "untitled"
        assert ken._slugify("   ") == "untitled"
        assert ken._slugify("///") == "untitled"

    def test_strips_diacritics_keeps_base_letter(self):
        # The whole point of #740 — accents must not collapse to dashes.
        assert ken._slugify("oublié") == "oublie"
        assert ken._slugify("authentifié") == "authentifie"
        assert ken._slugify("cassés") == "casses"
        assert ken._slugify("hôtel") == "hotel"
        assert ken._slugify("ça va") == "ca-va"
        assert ken._slugify("über") == "uber"
        assert ken._slugify("naïve") == "naive"

    def test_strips_diacritics_in_mixed_strings(self):
        assert (
            ken._slugify("DOC / README / liens cassés vers doc/*.md")
            == "doc-readme-liens-casses-vers-doc-md"
        )
        assert (
            ken._slugify("test e2e mot de passe oublié")
            == "test-e2e-mot-de-passe-oublie"
        )

    def test_task_filename_uses_diacritic_aware_slug(self):
        assert (
            ken._task_filename({"task_id": 237, "title": "mot de passe oublié"})
            == "mot-de-passe-oublie-237.md"
        )


class TestSidebarNav:
    """``_format_sidebar_nav`` builds file://-safe relative hrefs (#741)."""

    @staticmethod
    def _sections():
        from dashboard.wiki import Section

        return [
            Section(
                id="backend",
                title="Backend",
                sub=[Section(id="api", title="REST API")],
            ),
            Section(id="docs", title="Documentation"),
        ]

    @staticmethod
    def _home_href(html: str) -> str:
        m = re.search(r'<a href="([^"]+)"[^>]*>Home</a>', html)
        assert m, f"no Home link found in {html!r}"
        return m.group(1)

    @staticmethod
    def _section_href(html: str, section_title: str) -> str:
        m = re.search(
            rf'<a href="([^"]+)"[^>]*>{section_title}</a>',
            html,
        )
        assert m, f"no {section_title} link found in {html!r}"
        return m.group(1)

    def test_root_index_emits_bare_hrefs(self):
        html = ken._format_sidebar_nav(self._sections(), "index.md", "")
        assert self._home_href(html) == "index.html"
        assert self._section_href(html, "Backend") == "backend/index.html"
        assert self._section_href(html, "REST API") == "backend/api/index.html"
        assert 'class="current"' in html  # Home is current

    def test_root_level_file_uses_zero_up_dirs(self):
        # log.md sits at root, so links shouldn't climb any directory.
        html = ken._format_sidebar_nav(self._sections(), "log.md", None)
        # No Home link when current_section is None.
        assert "Home</a>" not in html
        assert self._section_href(html, "Backend") == "backend/index.html"

    def test_section_index_climbs_one_level(self):
        html = ken._format_sidebar_nav(self._sections(), "docs/index.md", "docs")
        # #741 — Home was "index.html" (resolves to docs/index.html), now ../.
        assert self._home_href(html) == "../index.html"
        assert self._section_href(html, "Backend") == "../backend/index.html"
        assert self._section_href(html, "Documentation") == "../docs/index.html"
        assert 'href="../docs/index.html" class="current"' in html

    def test_task_page_in_section_climbs_one_level(self):
        html = ken._format_sidebar_nav(
            self._sections(),
            "docs/foo-1.md",
            "docs",
        )
        # Task page sits in docs/, same depth as docs/index.html.
        assert self._home_href(html) == "../index.html"
        assert self._section_href(html, "Documentation") == "../docs/index.html"

    def test_nested_section_climbs_two_levels(self):
        # #741 — Home was "../index.html" (resolves to backend/index.html),
        # now correctly "../../index.html".
        html = ken._format_sidebar_nav(
            self._sections(),
            "backend/api/index.md",
            "backend/api",
        )
        assert self._home_href(html) == "../../index.html"
        assert self._section_href(html, "Backend") == "../../backend/index.html"
        assert self._section_href(html, "REST API") == "../../backend/api/index.html"

    def test_task_page_in_nested_section_climbs_two_levels(self):
        html = ken._format_sidebar_nav(
            self._sections(),
            "backend/api/foo-1.md",
            "backend/api",
        )
        assert self._home_href(html) == "../../index.html"
        assert self._section_href(html, "REST API") == "../../backend/api/index.html"

    def test_no_home_when_current_section_none(self):
        html = ken._format_sidebar_nav(self._sections(), "log.md", None)
        assert "Home</a>" not in html


class TestCliSync:
    """`ken sync` mirrors tasks to a directory and persists sync_dir."""

    def _setup(self, cwd_tmp):
        (cwd_tmp / ".ken").write_text("project_id=p1\n")
        os.chmod(cwd_tmp / ".ken", 0o600)

    def test_no_project_fails(self, cwd_tmp, runner):
        result = runner.invoke(ken.cli, ["sync"])
        assert result.exit_code != 0
        assert "no project configured" in result.output

    def test_writes_one_file_per_task(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
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
                            "position": 0,
                            "created_at": "2026-04-09T10:00:00",
                            "updated_at": "2026-04-09T10:00:00",
                            "title": "First",
                            "description": "alpha",
                        },
                        {
                            "id": 42,
                            "status": "doing",
                            "who": "Claude",
                            "due_date": "2026-04-15",
                            "position": 1,
                            "created_at": "2026-04-09T11:00:00",
                            "updated_at": "2026-04-09T12:00:00",
                            "title": "AGENT / CLI / sync",
                            "description": "beta",
                        },
                    ],
                )
            ]
        )
        with ctx:
            result = runner.invoke(ken.cli, ["sync"])
        assert result.exit_code == 0, result.output
        target = cwd_tmp / "doc" / "kenboard"
        assert (target / "0001 - First.md").exists()
        assert (target / "0042 - AGENT _ CLI _ sync.md").exists()
        body = (target / "0042 - AGENT _ CLI _ sync.md").read_text(encoding="utf-8")
        assert "id: 42" in body
        assert "# AGENT / CLI / sync" in body
        assert "beta" in body
        assert "Synced 2 task(s)" in result.output

    def test_persists_sync_dir_to_ken(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        ctx, _ = _patch_responses([("GET", "/api/v1/tasks?project=p1", [])])
        with ctx:
            result = runner.invoke(ken.cli, ["sync"])
        assert result.exit_code == 0, result.output
        ken_text = (cwd_tmp / ".ken").read_text(encoding="utf-8")
        assert "sync_dir=doc/kenboard" in ken_text

    def test_does_not_duplicate_sync_dir_line(self, cwd_tmp, runner):
        (cwd_tmp / ".ken").write_text("project_id=p1\nsync_dir=custom/path\n")
        os.chmod(cwd_tmp / ".ken", 0o600)
        ctx, _ = _patch_responses([("GET", "/api/v1/tasks?project=p1", [])])
        with ctx:
            result = runner.invoke(ken.cli, ["sync"])
        assert result.exit_code == 0, result.output
        ken_text = (cwd_tmp / ".ken").read_text(encoding="utf-8")
        assert ken_text.count("sync_dir=") == 1
        # Custom path was used, not the default
        assert (cwd_tmp / "custom" / "path").is_dir()

    def test_renames_file_when_title_changes(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        target = cwd_tmp / "doc" / "kenboard"
        target.mkdir(parents=True)
        stale = target / "0005 - Old Title.md"
        stale.write_text("stale\n")
        ctx, _ = _patch_responses(
            [
                (
                    "GET",
                    "/api/v1/tasks?project=p1",
                    [{"id": 5, "title": "New Title", "description": ""}],
                )
            ]
        )
        with ctx:
            result = runner.invoke(ken.cli, ["sync"])
        assert result.exit_code == 0, result.output
        assert not stale.exists()
        assert (target / "0005 - New Title.md").exists()

    def test_removes_stale_files(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        target = cwd_tmp / "doc" / "kenboard"
        target.mkdir(parents=True)
        ghost = target / "0099 - Removed.md"
        ghost.write_text("ghost\n")
        ctx, _ = _patch_responses(
            [
                (
                    "GET",
                    "/api/v1/tasks?project=p1",
                    [{"id": 1, "title": "Kept", "description": ""}],
                )
            ]
        )
        with ctx:
            result = runner.invoke(ken.cli, ["sync"])
        assert result.exit_code == 0, result.output
        assert not ghost.exists()
        assert (target / "0001 - Kept.md").exists()
        assert "Removed 1 stale file(s)" in result.output

    def test_leaves_unrelated_files_alone(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        target = cwd_tmp / "doc" / "kenboard"
        target.mkdir(parents=True)
        readme = target / "README.md"
        readme.write_text("hand-written\n")
        ctx, _ = _patch_responses([("GET", "/api/v1/tasks?project=p1", [])])
        with ctx:
            result = runner.invoke(ken.cli, ["sync"])
        assert result.exit_code == 0, result.output
        assert readme.exists()
        assert readme.read_text(encoding="utf-8") == "hand-written\n"

    def test_json_output_lists_changes(self, cwd_tmp, runner):
        self._setup(cwd_tmp)
        ctx, _ = _patch_responses(
            [
                (
                    "GET",
                    "/api/v1/tasks?project=p1",
                    [{"id": 1, "title": "Hi", "description": ""}],
                )
            ]
        )
        with ctx:
            result = runner.invoke(ken.cli, ["sync", "--json"])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["written"] == ["0001 - Hi.md"]
        assert payload["deleted"] == []
        assert os.path.join("doc", "kenboard") in payload["target"]


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
