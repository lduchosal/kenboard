"""End-to-end tests for ``ken`` CLI against a live Flask server.

Reuses the ``live_server`` and ``clean_db`` fixtures from
``tests/e2e/conftest.py``. The CLI is exercised via ``CliRunner`` so we don't
spawn a subprocess — but every command goes through the real
``urllib.request`` → live Flask → real test database round trip.
"""

import json
import os

import pytest
from click.testing import CliRunner

from dashboard import ken


@pytest.fixture()
def runner():
    return CliRunner()


@pytest.fixture()
def project_id(live_server, clean_db):
    """Create a category + project via the API and return the project_id."""
    import urllib.request as ur

    base = live_server

    def _post(path, body):
        req = ur.Request(
            base + path,
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with ur.urlopen(req) as resp:
            return json.loads(resp.read())

    cat = _post("/api/v1/categories", {"name": "Tech", "color": "#0969da"})
    proj = _post(
        "/api/v1/projects",
        {"cat": cat["id"], "name": "Demo", "acronym": "DEMO"},
    )
    return proj["id"]


@pytest.fixture()
def cwd_tmp(tmp_path, monkeypatch):
    """Run from a clean tmp dir with KEN_* env vars cleared."""
    monkeypatch.chdir(tmp_path)
    for key in ("KEN_PROJECT_ID", "KEN_BASE_URL", "KEN_API_TOKEN"):
        monkeypatch.delenv(key, raising=False)
    return tmp_path


def _ken(runner, live_server, *args):
    """Invoke ken with --base-url pointing at the live server."""
    return runner.invoke(ken.cli, ["--base-url", live_server, *args])


def _ken_with_project(runner, live_server, project_id, *args):
    return runner.invoke(
        ken.cli,
        ["--base-url", live_server, "--project", project_id, *args],
    )


class TestKenE2E:
    """Ken commands against a live Flask server + real DB."""

    def test_projects_lists_created_project(
        self, runner, live_server, clean_db, project_id, cwd_tmp
    ):
        result = _ken(runner, live_server, "projects", "--json")
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert any(p["id"] == project_id for p in data)

    def test_init_writes_ken_file(
        self, runner, live_server, clean_db, project_id, cwd_tmp
    ):
        # Pretend we're in a git repo so .gitignore handling fires
        (cwd_tmp / ".git").mkdir()
        result = _ken(runner, live_server, "init", project_id)
        assert result.exit_code == 0, result.output
        ken_file = cwd_tmp / ".ken"
        assert ken_file.exists()
        content = ken_file.read_text()
        assert f"project_id={project_id}" in content
        assert f"base_url={live_server}" in content
        # 0600
        assert (ken_file.stat().st_mode & 0o777) == 0o600
        # gitignore updated
        assert ".ken" in (cwd_tmp / ".gitignore").read_text().splitlines()

    def test_full_lifecycle(self, runner, live_server, clean_db, project_id, cwd_tmp):
        """Add → list → update → move → done → show on a real DB."""
        # Create
        result = _ken_with_project(
            runner,
            live_server,
            project_id,
            "add",
            "First task",
            "--who",
            "Q",
            "--json",
        )
        assert result.exit_code == 0, result.output
        task = json.loads(result.output)
        task_id = task["id"]
        assert task["title"] == "First task"
        assert task["status"] == "todo"

        # List
        result = _ken_with_project(runner, live_server, project_id, "list", "--json")
        assert result.exit_code == 0, result.output
        assert len(json.loads(result.output)) == 1

        # Update title
        result = _ken_with_project(
            runner,
            live_server,
            project_id,
            "update",
            str(task_id),
            "--title",
            "Renamed",
            "--json",
        )
        assert result.exit_code == 0, result.output
        assert json.loads(result.output)["title"] == "Renamed"

        # Move to doing
        result = _ken_with_project(
            runner,
            live_server,
            project_id,
            "move",
            str(task_id),
            "--to",
            "doing",
        )
        assert result.exit_code == 0, result.output
        assert "→ doing" in result.output

        # Mark done
        result = _ken_with_project(
            runner, live_server, project_id, "done", str(task_id)
        )
        assert result.exit_code == 0, result.output
        assert "→ done" in result.output

        # Show
        result = _ken_with_project(
            runner,
            live_server,
            project_id,
            "show",
            str(task_id),
            "--json",
        )
        assert result.exit_code == 0, result.output
        final = json.loads(result.output)
        assert final["title"] == "Renamed"
        assert final["status"] == "done"

    def test_list_status_filter_against_live(
        self, runner, live_server, clean_db, project_id, cwd_tmp
    ):
        # Seed a few tasks in different statuses
        for title, status in [
            ("T1", "todo"),
            ("T2", "doing"),
            ("T3", "doing"),
            ("T4", "done"),
        ]:
            r = _ken_with_project(
                runner,
                live_server,
                project_id,
                "add",
                title,
                "--status",
                status,
                "--json",
            )
            assert r.exit_code == 0, r.output

        result = _ken_with_project(
            runner,
            live_server,
            project_id,
            "list",
            "--status",
            "doing",
            "--json",
        )
        assert result.exit_code == 0, result.output
        tasks = json.loads(result.output)
        titles = sorted(t["title"] for t in tasks)
        assert titles == ["T2", "T3"]

    def test_walk_up_parents_finds_ken(
        self, runner, live_server, clean_db, project_id, cwd_tmp
    ):
        """Ken init at the root, then commands from a deep subdir."""
        (cwd_tmp / ".git").mkdir()
        result = _ken(runner, live_server, "init", project_id)
        assert result.exit_code == 0, result.output

        deep = cwd_tmp / "a" / "b" / "c"
        deep.mkdir(parents=True)
        os.chdir(deep)

        # No --project flag, the .ken at the root must be picked up
        result = runner.invoke(ken.cli, ["--base-url", live_server, "list", "--json"])
        assert result.exit_code == 0, result.output
        assert json.loads(result.output) == []
