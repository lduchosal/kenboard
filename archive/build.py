#!/usr/bin/env python3
"""Generate static dashboard pages from data.json using Jinja2 templates."""

import json
import os
from datetime import date
from html.parser import HTMLParser

from jinja2 import Environment, FileSystemLoader

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(HERE, "src", "dashboard", "templates")

with open(os.path.join(HERE, "data.json")) as f:
    data = json.load(f)

categories = data["categories"]
projects = data["projects"]

# -- Constants ----------------------------------------------------------------

COLUMNS = [
    {"id": "todo", "name": "A faire", "color": "var(--todo)"},
    {"id": "doing", "name": "En cours", "color": "var(--cyan)"},
    {"id": "review", "name": "Revue", "color": "var(--purple)"},
    {"id": "done", "name": "Fait", "color": "var(--green)"},
]

COLOR_LIST = [
    ("Orange", "var(--orange)"),
    ("Vert", "var(--green)"),
    ("Bleu", "var(--accent)"),
    ("Violet", "var(--purple)"),
    ("Cyan", "var(--cyan)"),
    ("Rouge", "var(--red)"),
    ("Rose", "var(--todo)"),
    ("Jaune", "var(--yellow)"),
    ("Gris", "var(--dimmed)"),
]

AVATAR_COLORS = {
    "Q": "#0969da",
    "Alice": "#8250df",
    "Bob": "#bf8700",
    "Claire": "#1a7f37",
}


# -- Helpers ------------------------------------------------------------------

def fmt_date(when_str: str) -> str:
    """Format ISO date to dd.mm."""
    d = date.fromisoformat(when_str)
    return f"{d.day:02d}.{d.month:02d}"


def aggregate_burndown(project_list: list) -> list:
    """Aggregate burndown actual values across projects."""
    if not project_list:
        return [0]
    length = len(project_list[0]["actual"])
    return [sum(p["actual"][i] for p in project_list) for i in range(length)]


def cat_projects_json() -> str:
    """Generate JSON for CAT_PROJECTS JS variable."""
    result = {}
    for c in categories:
        result[c["id"]] = [
            {
                "id": p["id"],
                "name": p["name"],
                "acronym": p.get("acronym", p["name"][:4].upper()),
                "tasks": len(p.get("tasks", [])),
            }
            for p in projects
            if p["cat"] == c["id"]
        ]
    return json.dumps(result)


# -- Jinja2 setup ------------------------------------------------------------

env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=True,
    trim_blocks=True,
    lstrip_blocks=True,
)

def jsesc(s: str) -> str:
    """Escape a string for use inside JS single-quoted strings."""
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")


env.filters["jsesc"] = jsesc

# Register custom functions as globals
env.globals.update(
    categories=categories,
    projects=projects,
    columns=COLUMNS,
    color_list=COLOR_LIST,
    avatar_colors=AVATAR_COLORS,
    fmt_date=fmt_date,
    aggregate_burndown=aggregate_burndown,
)


def build_context(prefix: str = "", current_cat: dict = None) -> dict:
    """Build shared template context."""
    projects_by_cat = {}
    cat_project_counts = {}
    for c in categories:
        cp = [p for p in projects if p["cat"] == c["id"]]
        projects_by_cat[c["id"]] = cp
        cat_project_counts[c["id"]] = len(cp)

    return {
        "prefix": prefix,
        "current_cat": current_cat,
        "projects_by_cat": projects_by_cat,
        "cat_project_counts": cat_project_counts,
        "cat_projects_json": cat_projects_json(),
    }


# -- Build pages --------------------------------------------------------------

def build_index() -> str:
    """Build the dashboard index page."""
    tpl = env.get_template("index.html")
    ctx = build_context(prefix="")
    ctx["title"] = "Dashboard"
    return tpl.render(**ctx)


def build_cat(cat: dict) -> str:
    """Build a category detail page."""
    tpl = env.get_template("category.html")
    cp = [p for p in projects if p["cat"] == cat["id"]]
    ctx = build_context(prefix="../", current_cat=cat)
    ctx["title"] = cat["name"]
    ctx["cat"] = cat
    ctx["active_projects"] = [p for p in cp if p.get("status", "active") == "active"]
    ctx["archived_projects"] = [p for p in cp if p.get("status") == "archived"]
    return tpl.render(**ctx)


# -- HTML validation ----------------------------------------------------------

VOID_TAGS = {
    "br", "hr", "img", "input", "meta", "link",
    "area", "base", "col", "embed", "source", "track", "wbr",
}


class TagChecker(HTMLParser):
    """Check HTML tag balance."""

    def __init__(self) -> None:
        super().__init__()
        self.stack: list = []
        self.errors: list = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        """Track opening tags."""
        if tag not in VOID_TAGS:
            self.stack.append((tag, self.getpos()))

    def handle_endtag(self, tag: str) -> None:
        """Check closing tags match."""
        if tag in VOID_TAGS:
            return
        if self.stack and self.stack[-1][0] == tag:
            self.stack.pop()
        else:
            expected = self.stack[-1][0] if self.stack else "none"
            self.errors.append(
                f"Line {self.getpos()[0]}: </{tag}> expected </{expected}>"
            )


def validate_html(filepath: str) -> bool:
    """Validate HTML tag balance in a file."""
    with open(filepath) as f:
        checker = TagChecker()
        checker.feed(f.read())
    ok = not checker.errors and not checker.stack
    if checker.errors:
        for e in checker.errors[:5]:
            print(f"  ERROR {e}")
    if checker.stack:
        print(f"  UNCLOSED {[(t, l) for t, l in checker.stack[:5]]}")
    return ok


# -- Main ---------------------------------------------------------------------

def main() -> None:
    """Generate all static HTML pages."""
    all_ok = True

    # Index
    path = os.path.join(HERE, "index.html")
    with open(path, "w") as f:
        f.write(build_index())
    ok = validate_html(path)
    print(f"index.html {'OK' if ok else 'FAIL'}")
    all_ok = all_ok and ok

    # Categories
    os.makedirs(os.path.join(HERE, "cat"), exist_ok=True)
    for c in categories:
        path = os.path.join(HERE, "cat", f'{c["id"]}.html')
        with open(path, "w") as f:
            f.write(build_cat(c))
        ok = validate_html(path)
        print(f'cat/{c["id"]}.html {"OK" if ok else "FAIL"}')
        all_ok = all_ok and ok

    print(f"\nDone: 1 index + {len(categories)} categories")
    if not all_ok:
        print("WARNING: HTML validation errors!")
        exit(1)


if __name__ == "__main__":
    main()
