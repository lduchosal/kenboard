"""Allowlist HTML sanitizer for ``ken wiki build`` (#1186).

Task descriptions are markdown written by whoever holds a write scope on a project —
users, api keys, LLM agents. Markdown lets raw HTML through, and the built wiki is
static HTML that gets published on origins shared with other tools, so everything
rendered from a task goes through :func:`sanitize_html` first.

The output is **re-serialised** from the parsed token stream, never copied from the
input: only allowlisted tags and attributes are emitted, every attribute value and text
node is escaped again. Nothing the parser did not understand can reach the page.
"""

from __future__ import annotations

import re
from html import escape
from html.parser import HTMLParser

# What python-markdown (+ fenced_code, tables) emits, plus the handful of inline
# HTML tags people legitimately type in a description.
_ALLOWED_TAGS = frozenset(
    {
        *("h1", "h2", "h3", "h4", "h5", "h6", "p", "br", "hr", "div", "span"),
        *("ul", "ol", "li", "dl", "dt", "dd", "blockquote", "pre", "code"),
        *("em", "strong", "b", "i", "u", "s", "del", "ins", "mark", "sub", "sup"),
        *("kbd", "abbr", "details", "summary", "a", "img"),
        *("table", "thead", "tbody", "tfoot", "tr", "th", "td", "caption"),
    }
)
_VOID_TAGS = frozenset({"br", "hr", "img"})
# Elements whose *content* must go too — script source, CSS, foreign content, and
# the raw-text / fallback containers HTML parsers disagree on.
_DROP_CONTENT = frozenset(
    {
        *("script", "style", "iframe", "object", "noscript", "template", "svg"),
        *("math", "textarea", "title", "select", "xmp", "noembed", "noframes"),
    }
)
_URL_ATTRS = frozenset({"href", "src"})
_ALLOWED_ATTRS: dict[str, frozenset[str]] = {
    "a": frozenset({"href", "title"}),
    "img": frozenset({"src", "alt", "title", "width", "height"}),
    "code": frozenset({"class"}),
    "pre": frozenset({"class"}),
    "span": frozenset({"class"}),
    "div": frozenset({"class"}),
    "th": frozenset({"style", "colspan", "rowspan"}),
    "td": frozenset({"style", "colspan", "rowspan"}),
    "abbr": frozenset({"title"}),
    "ol": frozenset({"start"}),
}
_SAFE_SCHEMES = frozenset({"http", "https", "mailto"})
_SCHEME_RE = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.\-]*):")
# Browsers drop ASCII whitespace and control characters while parsing a URL, so
# ``java\tscript:`` is a scheme to them — strip the same set before looking.
_URL_IGNORED_RE = re.compile(r"[\x00-\x20\x7f]")
_CLASS_RE = re.compile(r"^[A-Za-z0-9_\- ]*$")
# The only inline style python-markdown's ``tables`` extension emits.
_TEXT_ALIGN_RE = re.compile(r"^text-align: ?(left|right|center);?$")
_NUMERIC_RE = re.compile(r"^[0-9]{1,4}$")


def _safe_url(value: str) -> bool:
    """Return True for relative URLs and ``http`` / ``https`` / ``mailto`` ones."""
    match = _SCHEME_RE.match(_URL_IGNORED_RE.sub("", value))
    return match is None or match.group(1).lower() in _SAFE_SCHEMES


def _attr_ok(name: str, value: str) -> bool:
    """Return True when an allowlisted attribute also carries a harmless value."""
    if name in _URL_ATTRS:
        return _safe_url(value)
    if name == "class":
        return _CLASS_RE.match(value) is not None
    if name == "style":
        return _TEXT_ALIGN_RE.match(value.strip()) is not None
    if name in {"width", "height", "colspan", "rowspan", "start"}:
        return _NUMERIC_RE.match(value) is not None
    return True


def _clean_attrs(tag: str, attrs: list[tuple[str, str | None]]) -> str:
    """Serialise the allowlisted attributes of ``tag`` (leading space included)."""
    allowed = _ALLOWED_ATTRS.get(tag, frozenset())
    out: list[str] = []
    for name, raw in attrs:
        value = raw or ""
        if name in allowed and _attr_ok(name, value):
            out.append(f' {name}="{escape(value, quote=True)}"')
    return "".join(out)


class _Sanitizer(HTMLParser):
    """Token-stream filter: emits allowlisted markup, escapes everything else."""

    def __init__(self) -> None:
        """Start with an empty output buffer and no open element."""
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self._open: list[str] = []
        self._dropping: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Emit an allowlisted start tag; open a drop zone for dangerous containers."""
        if self._dropping or tag in _DROP_CONTENT:
            if tag in _DROP_CONTENT:
                self._dropping.append(tag)
            return
        if tag not in _ALLOWED_TAGS:
            # Not markup we render: show it as the text the author typed. Task
            # descriptions are full of ``<id>`` / ``<cat_id>`` placeholders.
            self.out.append(escape(self.get_starttag_text() or "", quote=False))
            return
        self.out.append(f"<{tag}{_clean_attrs(tag, attrs)}>")
        if tag not in _VOID_TAGS:
            self._open.append(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Handle ``<tag/>`` — an unknown one was already emitted whole, as text."""
        self.handle_starttag(tag, attrs)
        if tag in _ALLOWED_TAGS or tag in _DROP_CONTENT:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        """Close ``tag`` if it is open — closing whatever was left open inside it."""
        if self._dropping:
            if tag == self._dropping[-1]:
                self._dropping.pop()
            return
        if tag not in _ALLOWED_TAGS and tag not in _DROP_CONTENT:
            self.out.append(escape(f"</{tag}>", quote=False))
            return
        if tag not in self._open:
            return
        while self._open:
            closing = self._open.pop()
            self.out.append(f"</{closing}>")
            if closing == tag:
                break

    def handle_data(self, data: str) -> None:
        """Emit text, escaped — unless it sits inside a dropped container."""
        if not self._dropping:
            self.out.append(escape(data, quote=False))

    def result(self) -> str:
        """Return the sanitised markup, with every dangling element closed."""
        self.close()
        tail = "".join(f"</{tag}>" for tag in reversed(self._open))
        self._open.clear()
        return "".join(self.out) + tail


def sanitize_html(html: str) -> str:
    """Return ``html`` reduced to the allowlisted tags, attributes and URL schemes.

    A tag outside the allowlist is shown as literal text (escaped), so a ``<id>``
    placeholder stays readable; ``<script>``, ``<style>`` and the other containers of
    ``_DROP_CONTENT`` are removed along with their content. An element left open is
    closed at the end, and a stray closing tag is ignored, so a description cannot break
    out of the page layout it is embedded in.
    """
    parser = _Sanitizer()
    parser.feed(html)
    return parser.result()
