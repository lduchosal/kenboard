"""Full-text search for the static wiki built by ``ken wiki build`` (#1178).

No server and no database: the build emits ``search-index.js`` (one JSON entry per task
page, assigned to ``window.KEN_WIKI_INDEX``), ``search.js`` (the vanilla scanner from
``wiki_search_js``) and ``search.html``. Every page carries a plain GET form pointing at
``search.html?q=…``, so only the search page pays for the index download.
"""

from __future__ import annotations

import json
import re
import unicodedata
from operator import itemgetter
from typing import Any

from dashboard.ken.wiki_detail import _strip_detail_chrome
from dashboard.ken.wiki_layout import _format_sidebar_nav, _wrap_html
from dashboard.ken.wiki_search_js import _WIKI_SEARCH_JS

_MD_LINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
_MD_LINE_PREFIX = re.compile(r"^\s*(?:#{1,6}|>)\s+", re.MULTILINE)
_MD_MARKS = re.compile(r"[`*~]+")
_SEARCH_PAGE = "search.html"


def _plain_text(md_text: str) -> str:
    """Flatten markdown to one line of searchable text.

    Deliberately crude: links keep their label, heading / quote prefixes and emphasis
    marks go, table pipes become spaces. ``_`` and inline ``#123`` are kept — snake_case
    identifiers and task references are what people search for. NFC-normalised so the
    client's accent folding maps one char to one char (highlight offsets stay valid).
    """
    text = _MD_LINK.sub(r"\1", md_text)
    text = _MD_LINE_PREFIX.sub("", text)
    text = _MD_MARKS.sub("", text).replace("|", " ")
    return unicodedata.normalize("NFC", " ".join(text.split()))


def _search_entry(html_path: str, meta: dict[str, Any], body_md: str) -> dict[str, Any]:
    """Build the index entry of one task detail page.

    ``html_path`` is the page's wiki-root-relative posix path — ``search.html`` sits
    at the root, so the client uses it as the href unchanged.
    """
    return {
        "id": int(meta["id"]),
        "title": unicodedata.normalize("NFC", str(meta.get("title") or "")),
        "section": str(meta.get("section") or ""),
        "status": str(meta.get("status") or ""),
        "path": html_path,
        "text": _plain_text(_strip_detail_chrome(body_md)),
    }


def _format_search_index_js(entries: list[dict[str, Any]]) -> str:
    """Serialise ``entries`` as the ``search-index.js`` payload.

    A ``.js`` assignment rather than ``.json`` + ``fetch`` so the wiki keeps working
    over ``file://``. One entry per line, sorted by task id, sorted keys: the file is
    committed alongside the HTML, so an edited task must diff as one line (#999).
    """
    lines = [
        json.dumps(e, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for e in sorted(entries, key=itemgetter("id"))
    ]
    return "window.KEN_WIKI_INDEX=[\n" + ",\n".join(lines) + "\n];\n"


def _search_files(
    entries: list[dict[str, Any]], sections: list, daily_dates: list[str]
) -> list[dict[str, str]]:
    """Return the three search files of the build plan (page, script, index).

    With an empty query the page lists every indexed task, newest first — it doubles
    as the wiki's flat index.
    """
    body = (
        "<h1>Recherche</h1>"
        '<div id="wiki-search-results"></div>'
        "<noscript><p>La recherche nécessite JavaScript.</p></noscript>"
        '<script src="search-index.js"></script><script src="search.js"></script>'
    )
    sidebar = _format_sidebar_nav(sections, _SEARCH_PAGE, "search", daily_dates)
    return [
        {
            "path": _SEARCH_PAGE,
            "content": _wrap_html("Recherche", body, sidebar, search_href=_SEARCH_PAGE),
        },
        {"path": "search.js", "content": _WIKI_SEARCH_JS},
        {"path": "search-index.js", "content": _format_search_index_js(entries)},
    ]
