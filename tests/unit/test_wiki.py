"""Wiki foundations: ARCHITECTURE.md parsing + classification queries (#376a).

Covers chunk A of the wiki feature: the schema parser (``parse_architecture``,
``section_paths``) and the aiosql queries that back the future ``ken wiki groom`` /
``ken wiki sync`` commands.
"""

from __future__ import annotations

import pytest

import dashboard.db as db_module
from dashboard.wiki import Section, parse_architecture, section_paths


@pytest.fixture()
def project(db):
    """Seed a category + project + a couple of tasks for classification tests."""
    cur = db.cursor()
    cur.execute(
        "INSERT INTO categories (id, name, color, position) VALUES (%s, %s, %s, %s)",
        ("cat-wiki", "Cat", "var(--accent)", 0),
    )
    cur.execute(
        "INSERT INTO projects (id, cat_id, name, acronym, status, position) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        ("proj-wiki", "cat-wiki", "Proj", "PROJ", "active", 0),
    )
    # Two tasks: one will get a classification, the other stays unclassified
    cur.execute(
        "INSERT INTO tasks (project_id, title, description, status, who, "
        "due_date, position) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        ("proj-wiki", "Task A", "", "todo", "Claude", None, 0),
    )
    task_a = cur.lastrowid
    cur.execute(
        "INSERT INTO tasks (project_id, title, description, status, who, "
        "due_date, position) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        ("proj-wiki", "Task B", "", "doing", "Q", None, 1),
    )
    task_b = cur.lastrowid
    return {"project_id": "proj-wiki", "task_a": task_a, "task_b": task_b}


# -- parse_architecture -------------------------------------------------------


class TestParseArchitecture:
    """Frontmatter extraction + Section tree construction."""

    def test_missing_file_returns_empty(self, tmp_path):
        assert parse_architecture(tmp_path / "nope.md") == []

    def test_no_frontmatter_returns_empty(self, tmp_path):
        p = tmp_path / "ARCHITECTURE.md"
        p.write_text("# Just a heading\n\nNo frontmatter here.\n", encoding="utf-8")
        assert parse_architecture(p) == []

    def test_empty_frontmatter_returns_empty(self, tmp_path):
        p = tmp_path / "ARCHITECTURE.md"
        p.write_text("---\n---\n\nbody\n", encoding="utf-8")
        assert parse_architecture(p) == []

    def test_frontmatter_without_wiki_key_returns_empty(self, tmp_path):
        p = tmp_path / "ARCHITECTURE.md"
        p.write_text("---\nother: thing\n---\n", encoding="utf-8")
        assert parse_architecture(p) == []

    def test_flat_sections(self, tmp_path):
        p = tmp_path / "ARCHITECTURE.md"
        p.write_text(
            "---\n"
            "wiki:\n"
            "  sections:\n"
            "    - id: backend\n"
            "      title: Backend\n"
            "      description: Flask routes\n"
            "    - id: frontend\n"
            "      title: Frontend\n"
            "---\n",
            encoding="utf-8",
        )
        sections = parse_architecture(p)
        assert len(sections) == 2
        assert sections[0] == Section(
            id="backend", title="Backend", description="Flask routes"
        )
        assert sections[1].id == "frontend"
        assert sections[1].sub == []

    def test_nested_sections(self, tmp_path):
        p = tmp_path / "ARCHITECTURE.md"
        p.write_text(
            "---\n"
            "wiki:\n"
            "  sections:\n"
            "    - id: backend\n"
            "      title: Backend\n"
            "      sub:\n"
            "        - id: api\n"
            "          title: REST API\n"
            "        - id: db\n"
            "          title: Database\n"
            "---\n",
            encoding="utf-8",
        )
        sections = parse_architecture(p)
        assert len(sections) == 1
        assert len(sections[0].sub) == 2
        assert sections[0].sub[0].id == "api"
        assert sections[0].sub[1].id == "db"

    def test_section_without_id_is_skipped(self, tmp_path):
        """Guard against incomplete YAML — drop sections lacking the id key."""
        p = tmp_path / "ARCHITECTURE.md"
        p.write_text(
            "---\n"
            "wiki:\n"
            "  sections:\n"
            "    - title: No id here\n"
            "    - id: backend\n"
            "---\n",
            encoding="utf-8",
        )
        sections = parse_architecture(p)
        assert [s.id for s in sections] == ["backend"]

    def test_title_falls_back_to_id_when_missing(self, tmp_path):
        p = tmp_path / "ARCHITECTURE.md"
        p.write_text(
            "---\n"  "wiki:\n"  "  sections:\n"  "    - id: ops\n"  "---\n",
            encoding="utf-8",
        )
        sections = parse_architecture(p)
        assert sections[0].title == "ops"


# -- section_paths ------------------------------------------------------------


class TestSectionPaths:
    """Flatten the section tree to ``parent/child`` paths."""

    def test_flat(self):
        sections = [Section(id="a", title="A"), Section(id="b", title="B")]
        assert section_paths(sections) == ["a", "b"]

    def test_nested(self):
        sections = [
            Section(
                id="backend",
                title="Backend",
                sub=[Section(id="api", title="API"), Section(id="db", title="DB")],
            ),
            Section(id="ops", title="Ops"),
        ]
        assert section_paths(sections) == [
            "backend",
            "backend/api",
            "backend/db",
            "ops",
        ]


# -- aiosql queries -----------------------------------------------------------


class TestWikiClassifyQuery:
    """``wiki_classify!`` upserts; ``wiki_clear!`` removes; ``wiki_get_*`` reads."""

    def test_classify_inserts(self, db, project):
        queries = db_module.load_queries()
        queries.wiki_classify(
            db,
            task_id=project["task_a"],
            section_path="backend/api",
            classified_by="Claude",
        )
        row = queries.wiki_get_for_task(db, task_id=project["task_a"])
        assert row is not None
        assert row["section_path"] == "backend/api"
        assert row["classified_by"] == "Claude"

    def test_classify_upserts_on_repeat(self, db, project):
        queries = db_module.load_queries()
        queries.wiki_classify(
            db,
            task_id=project["task_a"],
            section_path="backend/api",
            classified_by="Claude",
        )
        # Re-classify to a different section
        queries.wiki_classify(
            db,
            task_id=project["task_a"],
            section_path="frontend/ui",
            classified_by="Q",
        )
        row = queries.wiki_get_for_task(db, task_id=project["task_a"])
        assert row["section_path"] == "frontend/ui"
        assert row["classified_by"] == "Q"
        # Only one row (UNIQUE on task_id enforced)
        cur = db.cursor()
        cur.execute(
            "SELECT COUNT(*) AS c FROM task_wiki_classifications WHERE task_id = %s",
            (project["task_a"],),
        )
        assert cur.fetchone()["c"] == 1

    def test_clear_removes_classification(self, db, project):
        queries = db_module.load_queries()
        queries.wiki_classify(
            db,
            task_id=project["task_a"],
            section_path="backend/api",
            classified_by="Claude",
        )
        queries.wiki_clear(db, task_id=project["task_a"])
        assert queries.wiki_get_for_task(db, task_id=project["task_a"]) is None

    def test_get_all_returns_join_with_task_title(self, db, project):
        queries = db_module.load_queries()
        queries.wiki_classify(
            db,
            task_id=project["task_a"],
            section_path="backend/api",
            classified_by="Claude",
        )
        queries.wiki_classify(
            db,
            task_id=project["task_b"],
            section_path="frontend/ui",
            classified_by="Q",
        )
        rows = list(queries.wiki_get_all(db))
        assert len(rows) == 2
        paths = {r["task_id"]: (r["section_path"], r["title"]) for r in rows}
        assert paths[project["task_a"]] == ("backend/api", "Task A")
        assert paths[project["task_b"]] == ("frontend/ui", "Task B")

    def test_get_unclassified_excludes_classified_tasks(self, db, project):
        queries = db_module.load_queries()
        # Initially both tasks are unclassified
        unclassified = list(queries.wiki_get_unclassified_tasks(db))
        ids = {r["id"] for r in unclassified}
        assert {project["task_a"], project["task_b"]} <= ids
        # Classify task_a; it disappears from the list
        queries.wiki_classify(
            db,
            task_id=project["task_a"],
            section_path="backend",
            classified_by="Claude",
        )
        unclassified = list(queries.wiki_get_unclassified_tasks(db))
        ids = {r["id"] for r in unclassified}
        assert project["task_a"] not in ids
        assert project["task_b"] in ids

    def test_task_delete_cascades_to_classification(self, db, project):
        """FK ON DELETE CASCADE: removing a task drops its classification too."""
        queries = db_module.load_queries()
        queries.wiki_classify(
            db,
            task_id=project["task_a"],
            section_path="backend",
            classified_by="Claude",
        )
        cur = db.cursor()
        cur.execute("DELETE FROM tasks WHERE id = %s", (project["task_a"],))
        assert queries.wiki_get_for_task(db, task_id=project["task_a"]) is None
