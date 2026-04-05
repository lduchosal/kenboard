#!/usr/bin/env python3
"""Generate static dashboard pages from data.json."""

import json
import os
from datetime import date
from html import escape

HERE = os.path.dirname(os.path.abspath(__file__))
NOW = date(2026, 4, 5)

with open(os.path.join(HERE, "data.json")) as f:
    data = json.load(f)

categories = data["categories"]
projects = data["projects"]

cat_map = {c["id"]: c for c in categories}
COLUMNS = [
    ("todo", "A faire", "var(--dimmed)"),
    ("doing", "En cours", "var(--cyan)"),
    ("review", "Revue", "var(--purple)"),
    ("done", "Fait", "var(--green)"),
]


def time_ago(due_str: str) -> str:
    d = date.fromisoformat(due_str)
    diff = (NOW - d).days
    if diff > 0:
        if diff < 7: return f"{diff}d ago"
        if diff < 30: return f"{round(diff/7)}w ago"
        if diff < 365: return f"{round(diff/30)}mo ago"
        return f"{round(diff/365)}y ago"
    left = -diff
    if left < 7: return f"in {left}d"
    if left < 30: return f"in {round(left/7)}w"
    if left < 365: return f"in {round(left/30)}mo"
    return f"in {round(left/365)}y"


def burndown_bars(actual: list, color: str) -> str:
    mx = max(actual) if actual else 1
    bars = []
    for v in actual:
        pct = v / mx * 100
        bars.append(
            f'<div class="bar-group"><div style="height:{pct:.0f}%;background:{color};opacity:0.5;border-radius:1px"></div></div>'
        )
    return "".join(bars)


def health_arrow(p: dict) -> tuple:
    li = p["ideal"][-1]
    la = p["actual"][-1]
    th = round(p["total"] * 0.2)
    if la <= li + 1: return ("↑", "var(--green)")
    if la <= li + th: return ("↗", "var(--orange)")
    return ("↓", "var(--red)")


def page(title: str, body: str, css_path: str = "style.css") -> str:
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<link rel="stylesheet" href="{css_path}">
</head>
<body>
{body}
</body>
</html>"""


def kanban_html(tasks: list, project_names: dict = None) -> str:
    html = '<div class="section" style="padding-bottom:0"><div class="kanban">'
    for col_id, col_name, col_color in COLUMNS:
        col_tasks = [t for t in tasks if t["status"] == col_id]
        html += f'<div class="kanban-col"><div class="kanban-col-header">'
        html += f'<span class="col-name" style="color:{col_color}">{col_name}</span>'
        html += f'<span class="col-count">{len(col_tasks)}</span></div>'
        for t in col_tasks:
            html += f'<div class="kanban-task"><div class="task-title">{escape(t["title"])}</div>'
            if project_names and "_project" in t:
                pname, pcolor = t["_project"], t["_color"]
                html += f'<div class="task-meta"><span class="task-tag" style="background:{pcolor}">{escape(pname)}</span></div>'
            html += '</div>'
        html += '</div>'
    html += '</div></div>'
    return html


# =====================================================================
# index.html — Dashboard
# =====================================================================
def build_index():
    header = """<div class="header">
  <h1>DASHBOARD</h1>
  <span class="meta">{n} projets</span>
  {badges}
  <span style="flex:1"></span>
  <span class="meta">2026-04-05 15:42 CET</span>
  <span class="badge" style="background:rgba(26,127,55,0.12);color:var(--green)">LIVE</span>
</div>"""

    badge_html = ""
    for c in categories:
        count = len([p for p in projects if p["cat"] == c["id"]])
        badge_html += f'<span class="badge" style="background:color-mix(in srgb, {c["color"]} 12%, transparent);color:{c["color"]}">{escape(c["name"])} {count}</span>\n  '

    header = header.format(n=len(projects), badges=badge_html)

    # Category cards
    cat_section = '<div class="section"><div class="section-title">Vue par categorie</div><div class="cat-grid">'
    for c in categories:
        cat_projects = [p for p in projects if p["cat"] == c["id"]]
        total_done = sum(p["done"] for p in cat_projects)
        total_tasks = sum(p["total"] for p in cat_projects)
        # Aggregate actual burndown
        length = len(cat_projects[0]["actual"])
        agg_actual = [sum(p["actual"][i] for p in cat_projects) for i in range(length)]

        cat_section += f'''<a class="cat-card" href="cat/{c["id"]}.html">
  <div class="cat-header">
    <div class="cat-dot" style="background:{c["color"]}"></div>
    <span class="cat-name">{escape(c["name"])}</span>
    <div class="cat-kpis"><div class="cat-kpi">
      <div class="value" style="color:var(--text)">{total_tasks - total_done}</div>
      <div class="label">Ouvertes</div>
    </div></div>
  </div>
  <div class="cat-burndown">{burndown_bars(agg_actual, c["color"])}</div>
</a>'''

    cat_section += '</div></div>'

    # Project cards
    proj_section = '<hr class="divider"><div class="section"><div class="section-title">Tous les projets</div><div class="grid">'
    for p in projects:
        c = cat_map[p["cat"]]
        arrow, acolor = health_arrow(p)
        proj_section += f'''<a class="card" data-cat="{p["cat"]}" href="project/{p["id"]}.html">
  <div class="card-header">
    <span class="name">{escape(p["name"])}</span>
    <span class="health" style="color:{acolor}">{arrow}</span>
    <span class="due">{time_ago(p["due"])}</span>
  </div>
  <div class="burndown">{burndown_bars(p["actual"], c["color"])}</div>
</a>'''

    proj_section += '</div></div>'

    return page("Dashboard", header + cat_section + proj_section)


# =====================================================================
# cat/{id}.html — Category kanban
# =====================================================================
def build_cat(cat: dict):
    cat_projects = [p for p in projects if p["cat"] == cat["id"]]
    total_done = sum(p["done"] for p in cat_projects)
    total_tasks = sum(p["total"] for p in cat_projects)

    header = f'''<div class="header">
  <a class="back-btn" href="../index.html">← Retour</a>
  <h1>{escape(cat["name"])}</h1>
  <span class="meta">{len(cat_projects)} projets — {total_tasks - total_done} taches ouvertes</span>
</div>'''

    body = ""
    for p in cat_projects:
        arrow, acolor = health_arrow(p)
        open_count = p["total"] - p["done"]
        body += f'''<div class="section">
  <div class="section-title" style="display:flex;align-items:center;gap:8px">
    <a href="../project/{p["id"]}.html" style="color:var(--text);text-decoration:none;font-size:13px;font-weight:700">{escape(p["name"])}</a>
    <span style="color:{acolor};font-size:12px">{arrow}</span>
    <span style="color:var(--dimmed);font-size:11px;font-weight:400">{open_count} ouvertes — {time_ago(p["due"])}</span>
  </div>
{kanban_html(p["tasks"])}
</div>'''

    return page(cat["name"], header + body, css_path="../style.css")


# =====================================================================
# project/{id}.html — Project kanban
# =====================================================================
def build_project(p: dict):
    c = cat_map[p["cat"]]
    header = f'''<div class="header">
  <a class="back-btn" href="../index.html">← Retour</a>
  <h1>{escape(p["name"])}</h1>
  <span class="badge" style="background:color-mix(in srgb, {c["color"]} 12%, transparent);color:{c["color"]}">{escape(c["name"])}</span>
  <span class="meta">{p["done"]}/{p["total"]} taches — {time_ago(p["due"])}</span>
</div>'''

    return page(p["name"], header + kanban_html(p["tasks"]), css_path="../style.css")


# =====================================================================
# Build all
# =====================================================================
def main():
    # index
    with open(os.path.join(HERE, "index.html"), "w") as f:
        f.write(build_index())
    print("index.html")

    # categories
    os.makedirs(os.path.join(HERE, "cat"), exist_ok=True)
    for c in categories:
        path = os.path.join(HERE, "cat", f'{c["id"]}.html')
        with open(path, "w") as f:
            f.write(build_cat(c))
        print(f'cat/{c["id"]}.html')

    # projects
    os.makedirs(os.path.join(HERE, "project"), exist_ok=True)
    for p in projects:
        path = os.path.join(HERE, "project", f'{p["id"]}.html')
        with open(path, "w") as f:
            f.write(build_project(p))
        print(f'project/{p["id"]}.html')

    print(f"\nDone: 1 index + {len(categories)} categories + {len(projects)} projects")


if __name__ == "__main__":
    main()
