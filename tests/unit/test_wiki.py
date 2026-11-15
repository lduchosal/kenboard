"""Wiki foundations: ARCHITECTURE.md parsing + classification queries (#376a).

Covers chunk A of the wiki feature: the schema parser (``parse_architecture``,
``section_paths``) and the aiosql queries that back the future ``ken wiki groom`` /
``ken wiki sync`` commands.
"""

from __future__ import annotations

import pytest

import dashboard.db as db_module
from dashboard.wiki import Section, parse_architecture, section_paths


@pytest.fixture
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
            "---\nwiki:\n  sections:\n    - id: ops\n---\n",
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


# -- #1186 — the built wiki never carries active content from a task ----------


class TestWikiSanitizer:
    """``sanitize_html`` — allowlist filter applied to every rendered page."""

    @pytest.mark.parametrize(
        "payload",
        [
            "<script>alert(1)</script>",
            "<img src=x onerror=alert(1)>",
            '<a href="javascript:alert(1)">x</a>',
            '<a href="java\tscript:alert(1)">x</a>',
            '<a href=" JaVaScRiPt:alert(1)">x</a>',
            '<a href="data:text/html,<script>alert(1)</script>">x</a>',
            "<svg onload=alert(1)><script>alert(1)</script></svg>",
            '<iframe src="https://evil.example"></iframe>',
            '<div style="background:url(javascript:alert(1))">x</div>',
            '<p onclick="alert(1)">x</p>',
            "<style>body{display:none}</style>",
            '<form action="https://evil.example"><input name=p></form>',
            '<meta http-equiv="refresh" content="0;url=https://evil.example">',
            '<base href="https://evil.example/">',
            '<object data="x"></object><embed src="x">',
            "<math><mtext><script>alert(1)</script></mtext></math>",
        ],
    )
    def test_active_content_is_removed(self, payload):
        """No tag, attribute or URL able to run code or load a document survives."""
        from dashboard.ken.wiki_sanitize import sanitize_html

        out = sanitize_html(payload).lower()
        assert "<script" not in out
        assert not [a for a in _attribute_names(out) if a.startswith("on")]
        hrefs = [v for k, v in _attributes(out) if k in ("href", "src")]
        assert not [v for v in hrefs if "script:" in v or v.startswith("data:")]
        for needle in ("<iframe", "<style", "<form", "<meta", "<base", "<object"):
            assert needle not in out
        assert "<embed" not in out
        assert "style" not in _attribute_names(out)

    def test_markdown_output_is_preserved(self):
        """What python-markdown emits for ordinary content goes through intact."""
        from dashboard.ken.wiki_detail import _render_markdown

        html = _render_markdown(
            "## Titre\n\nUn *texte* avec `code`, un [lien](https://example.org/a?b=1&c=2)"
            " et un [relatif](../x/index.md).\n\n"
            "```python\nprint('<b>')\n```\n\n"
            "| a | b |\n|:--|--:|\n| 1 | 2 |\n"
        )
        assert "<h2>Titre</h2>" in html
        assert "<em>texte</em>" in html
        assert '<a href="https://example.org/a?b=1&amp;c=2">lien</a>' in html
        assert '<a href="../x/index.md">relatif</a>' in html
        assert "print('&lt;b&gt;')" in html
        assert '<code class="language-python">' in html
        assert '<th style="text-align: left;">a</th>' in html
        assert '<td style="text-align: right;">2</td>' in html

    def test_unknown_tags_are_shown_as_text(self):
        """A tag outside the allowlist becomes literal text — placeholders survive."""
        from dashboard.ken.wiki_sanitize import sanitize_html

        assert sanitize_html("tasks/<id> a < b") == "tasks/&lt;id&gt; a &lt; b"
        assert (
            sanitize_html('<blink onclick="x()">hi</blink><foo/>')
            == '&lt;blink onclick="x()"&gt;hi&lt;/blink&gt;&lt;foo/&gt;'
        )

    def test_unbalanced_markup_cannot_escape_its_container(self):
        """Stray closing tags are dropped and dangling elements get closed."""
        from dashboard.ken.wiki_sanitize import sanitize_html

        assert sanitize_html("</div></div><div><b>x") == "<div><b>x</b></div>"

    def test_unclosed_dangerous_container_drops_the_rest(self):
        """An unterminated ``<svg>`` fails closed: nothing after it is emitted."""
        from dashboard.ken.wiki_sanitize import sanitize_html

        assert sanitize_html("ok<svg><p>hidden</p>") == "ok"


def _attributes(html: str) -> list[tuple[str, str]]:
    """Every ``(name, value)`` attribute a browser would see in ``html``."""
    from html.parser import HTMLParser

    found: list[tuple[str, str]] = []

    class _Collector(HTMLParser):
        def handle_starttag(self, tag, attrs):
            found.extend((name, value or "") for name, value in attrs)

    _Collector().feed(html)
    return found


def _attribute_names(html: str) -> list[str]:
    """Every attribute name a browser would see in ``html``."""
    return [name for name, _ in _attributes(html)]


class TestWikiDetailEscaping:
    """#1186 — task metadata is escaped in the detail page and the ``<title>``."""

    def test_frontmatter_values_are_escaped(self):
        """``who`` / ``title`` / ``classified_by`` are free text: never raw HTML."""
        from dashboard.ken.wiki_detail import _render_task_detail

        html = _render_task_detail(
            {
                "id": 7,
                "title": "a <b>title</b>",
                "status": 'x" onmouseover="alert(1)',
                "who": "<img src=x onerror=alert(1)>",
                "classified_by": "<script>alert(1)</script>",
                "classified_at": '"><script>',
                "section": "backend/api",
            },
            "<script>alert(2)</script>\n\ntexte",
        )
        assert "<script" not in html
        assert "<img" not in html
        assert not [a for a in _attribute_names(html) if a.startswith("on")]
        assert 'class="fullscreen-status "' in html
        assert "a &lt;b&gt;title&lt;/b&gt;" in html
        assert 'href="../../log/unknown.html"' in html
        assert "texte" in html

    def test_page_title_is_escaped(self):
        """A task title cannot close ``<title>`` and open a script."""
        from dashboard.ken.wiki_layout import _wrap_html

        html = _wrap_html("</title><script>alert(1)</script>", "<p>x</p>", "")
        assert "<script>alert(1)" not in html
        assert "&lt;/title&gt;" in html
