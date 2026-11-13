"""Unit tests for the static wiki's full-text search (#1178)."""

from __future__ import annotations

import json

from dashboard.ken.wiki_build import _build_html_plan
from dashboard.ken.wiki_layout import _wrap_html
from dashboard.ken.wiki_search import (
    _format_search_index_js,
    _plain_text,
    _search_entry,
)

_TASK_MD = """\
---
id: {id}
title: "{title}"
status: done
section: backend/api
---

# #{id} — {title}

Corps **important** de `wiki_build`, cf [la doc](../doc.md) et #856.

---

[← retour à backend/api](index.md) · [voir log](../../log/2026-05-24.md)
"""


def _index_entries(js: str) -> list[dict]:
    """Parse a ``search-index.js`` payload back into its entries."""
    prefix, suffix = "window.KEN_WIKI_INDEX=", ";\n"
    assert js.startswith(prefix)
    assert js.endswith(suffix)
    return json.loads(js[len(prefix) : -len(suffix)])


def _make_tree(root):
    """Write a two-task MD tree plus a section index under ``root``."""
    api = root / "backend" / "api"
    api.mkdir(parents=True)
    (root / "index.md").write_text("# kenboard wiki\n", encoding="utf-8")
    (api / "index.md").write_text("# REST API\n", encoding="utf-8")
    (api / "b-20.md").write_text(
        _TASK_MD.format(id=20, title="Sécurité B"), encoding="utf-8"
    )
    (api / "a-3.md").write_text(
        _TASK_MD.format(id=3, title="Tâche A"), encoding="utf-8"
    )


class TestPlainText:
    def test_strips_markup_keeps_identifiers_and_refs(self):
        out = _plain_text("## Titre\n\n> **gras** `snake_case` [lien](x.md) #856\n")
        assert out == "Titre gras snake_case lien #856"

    def test_table_pipes_and_whitespace_collapse(self):
        assert _plain_text("| a | b |\n|---|---|\n\n\nc") == "a b --- --- c"

    def test_nfc_normalises_decomposed_accents(self):
        # Client-side folding relies on one char per char for highlight offsets.
        assert _plain_text("été") == "été"


class TestSearchEntry:
    def test_entry_drops_page_chrome(self):
        body = _TASK_MD.format(id=7, title="T").split("---\n", 2)[2].lstrip("\n")
        entry = _search_entry("backend/api/t-7.html", {"id": "7", "title": "T"}, body)
        assert entry["id"] == 7
        assert entry["path"] == "backend/api/t-7.html"
        assert entry["text"].startswith("Corps important de wiki_build")
        assert "retour" not in entry["text"]
        assert "# #7" not in entry["text"]


class TestSearchIndexJs:
    def test_one_line_per_entry_sorted_by_id(self):
        js = _format_search_index_js(
            [{"id": 20, "title": "é"}, {"id": 3, "title": "a"}],
        )
        lines = js.splitlines()
        assert lines[0] == "window.KEN_WIKI_INDEX=["
        assert lines[1] == '{"id":3,"title":"a"},'
        assert lines[2] == '{"id":20,"title":"é"}'
        assert [e["id"] for e in _index_entries(js)] == [3, 20]

    def test_empty_index_is_valid(self):
        assert _index_entries(_format_search_index_js([])) == []


class TestBuildPlan:
    def test_plan_ships_search_page_script_and_index(self, tmp_path):
        _make_tree(tmp_path)
        plan = {f["path"]: f["content"] for f in _build_html_plan(tmp_path, [])}
        assert {"search.html", "search.js", "search-index.js"} <= set(plan)
        entries = _index_entries(plan["search-index.js"])
        # Only task pages are indexed — section/root indexes are link lists.
        assert [e["id"] for e in entries] == [3, 20]
        assert entries[1]["title"] == "Sécurité B"
        assert entries[1]["path"] == "backend/api/b-20.html"
        assert entries[1]["section"] == "backend/api"
        page = plan["search.html"]
        assert 'id="wiki-search-results"' in page
        assert page.index("search-index.js") < page.index('src="search.js"')

    def test_search_box_sits_in_main_with_depth_relative_action(self, tmp_path):
        _make_tree(tmp_path)
        plan = {f["path"]: f["content"] for f in _build_html_plan(tmp_path, [])}
        for path, action in (
            ("index.html", "search.html"),
            ("search.html", "search.html"),
            ("backend/api/index.html", "../../search.html"),
            ("backend/api/a-3.html", "../../search.html"),
        ):
            html = plan[path]
            form = f'<form class="wiki-search" action="{action}"'
            assert f"<main>{form}" in html, path
            sidebar = html[html.index("<nav") : html.index("</nav>")]
            assert "wiki-search" not in sidebar

    def test_regular_pages_load_no_script(self, tmp_path):
        _make_tree(tmp_path)
        plan = {f["path"]: f["content"] for f in _build_html_plan(tmp_path, [])}
        assert "<script" not in plan["backend/api/a-3.html"]

    def test_wrap_html_without_search_href_has_no_form(self):
        assert "<form" not in _wrap_html("t", "<p>b</p>", "<nav/>")
