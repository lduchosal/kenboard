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


COLUMNS = [
    ("todo", "A faire", "#d63384"),
    ("doing", "En cours", "var(--cyan)"),
    ("review", "Revue", "var(--purple)"),
    ("done", "Fait", "var(--green)"),
]


AVATAR_COLORS = {
    "Q": "#0969da",
    "Alice": "#8250df",
    "Bob": "#bf8700",
    "Claire": "#1a7f37",
}


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
    mx = max(actual) if actual and max(actual) > 0 else 1
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
<script src="https://cdn.jsdelivr.net/npm/sortablejs@1.15.6/Sortable.min.js"></script>
</head>
<body>
{body}
<script>
// Sticky title observer
const header = document.querySelector('.header');
let stuckCount = 0;
document.querySelectorAll('.section-title').forEach(el => {{
  const observer = new IntersectionObserver(
    ([e]) => {{
      const isStuck = e.intersectionRatio < 1;
      const wasStuck = el.classList.contains('stuck');
      el.classList.toggle('stuck', isStuck);
      if (isStuck && !wasStuck) stuckCount++;
      if (!isStuck && wasStuck) stuckCount--;
      header.classList.toggle('no-border', stuckCount > 0);
    }},
    {{ threshold: [1], rootMargin: '-42px 0px 0px 0px' }}
  );
  const sentinel = document.createElement('div');
  sentinel.style.height = '1px';
  sentinel.style.marginBottom = '-1px';
  el.before(sentinel);
  observer.observe(sentinel);
}});

// Add task
function addTask(btn) {{
  const form = btn.closest('.kanban-new-form');
  const title = form.querySelector('.new-task-title').value.trim();
  if (!title) return;
  const desc = form.querySelector('.new-task-desc').value.trim();
  const who = form.querySelector('.new-task-who').value;
  const when = form.querySelector('.new-task-when').value;
  fetch(`${{API_BASE}}/tasks`, {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/json' }},
    body: JSON.stringify({{ title, desc, who, when, status: 'todo' }})
  }}).catch(err => console.warn('API not available:', err));
  const col = form.closest('.kanban-col');
  const tasks = col.querySelector('.kanban-tasks');
  const card = document.createElement('div');
  card.className = 'kanban-task';
  card.innerHTML = `<div class="task-body"><div class="task-title">${{title}}</div>${{desc ? `<div class="task-desc">${{desc}}</div>` : ''}}</div>`;
  tasks.prepend(card);
  form.querySelector('.new-task-title').value = '';
  form.querySelector('.new-task-desc').value = '';
  form.querySelector('.new-task-when').value = '';
  form.style.display = 'none';
}}

function cancelAdd(btn) {{
  const form = btn.closest('.kanban-new-form');
  form.style.display = 'none';
}}

// Kanban drag & drop
const API_BASE = '/api/v1';

document.querySelectorAll('.kanban-col').forEach(col => {{
  const taskContainer = col.querySelector('.kanban-tasks');
  if (!taskContainer) return;
  new Sortable(taskContainer, {{
    group: 'kanban',
    animation: 150,
    draggable: '.kanban-task',
    ghostClass: 'task-ghost',
    chosenClass: 'task-chosen',
    dragClass: 'task-drag',
    onEnd: (evt) => {{
      const taskId = evt.item.dataset.taskId;
      const newStatus = evt.to.dataset.status;
      const newIndex = evt.newIndex;
      if (!taskId) return;
      fetch(`${{API_BASE}}/tasks/${{taskId}}`, {{
        method: 'PATCH',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ status: newStatus, position: newIndex }})
      }}).catch(err => console.warn('API not available:', err));
    }}
  }});
}});
</script>
</body>
</html>"""


def kanban_html(tasks: list, project_names: dict = None, show_edit: bool = False) -> str:
    todo_special_count = [0] if show_edit else [2]  # 0=detail, 1=edit, 2+=normal
    middle_cols = {"doing", "review"}
    rest_cols = {"doing", "review", "done"}
    html = '<div class="kanban">'
    in_rest = False
    in_middle = False
    for col_id, col_name, col_color in COLUMNS:
        if col_id in rest_cols and not in_rest:
            html += '<div class="kanban-rest">'
            in_rest = True
        if col_id in middle_cols and not in_middle:
            html += '<div class="kanban-middle">'
            in_middle = True
        elif col_id not in middle_cols and in_middle:
            html += '</div>'
            in_middle = False
        col_tasks = [t for t in tasks if t["status"] == col_id]
        html += f'<div class="kanban-col" style="background:color-mix(in srgb, {col_color} 5%, white)"><div class="kanban-col-header" style="background:color-mix(in srgb, {col_color} 25%, transparent)">'
        html += f'<span class="col-name" style="color:{col_color}">{col_name}</span>'
        if col_id == "todo":
            people_opts = "".join(f'<option>{escape(p)}</option>' for p in AVATAR_COLORS.keys())
            html += f'<button class="kanban-add-btn" onclick="this.closest(\'.kanban-col\').querySelector(\'.kanban-new-form\').style.display=\'block\'">+</button>'
        html += f'</div>'
        if col_id == "todo":
            html += f'<div class="kanban-task edit-mode kanban-new-form" style="display:none">'
            html += f'<div class="edit-row"><input type="text" class="new-task-title" placeholder="Titre" style="font-weight:600"></div>'
            html += f'<div class="edit-row"><textarea class="new-task-desc" placeholder="Detail"></textarea></div>'
            html += f'<div class="edit-row"><select class="new-task-who">{people_opts}</select><input type="text" class="new-task-when" placeholder="dd.mm" style="width:60px;flex:none"></div>'
            html += f'<div class="edit-actions"><button class="btn btn-save" onclick="addTask(this)">Enregistrer</button><button class="btn btn-cancel" onclick="cancelAdd(this)">Annuler</button></div>'
            html += f'</div>'
        html += f'<div class="kanban-tasks" data-status="{col_id}">'
        max_visible = 5 if col_id == "done" else None
        visible_tasks = col_tasks[:max_visible] if max_visible else col_tasks
        hidden_count = len(col_tasks) - len(visible_tasks)
        for t in visible_tasks:
            who = t.get("who", "?")
            initials = who[0].upper()
            avatar_color = AVATAR_COLORS.get(who, "var(--dimmed)")
            when_str = ""
            if t.get("when"):
                d = date.fromisoformat(t["when"])
                when_str = f'{d.day:02d}.{d.month:02d}'
            desc = escape(t.get("desc", ""))

            # First TODO: detail view (read-only expanded)
            if col_id == "todo" and todo_special_count[0] == 0:
                todo_special_count[0] = 1
                html += f'<div class="kanban-task detail-mode" data-task-id="{t.get("id", "")}">'
                html += f'<div class="task-body">'
                html += f'<div class="task-title">{escape(t["title"])}</div>'
                if desc:
                    html += f'<div class="task-desc-full">{desc}</div>'
                html += f'</div>'
                html += f'<div class="task-right">'
                html += f'<div class="task-avatar" style="background:{avatar_color}" title="{escape(who)}">{initials}</div>'
                if when_str:
                    html += f'<div class="task-when">{when_str}</div>'
                html += f'<button class="btn-edit">Editer</button>'
                html += f'</div>'
                html += f'</div>'

            # Second TODO: edit mode
            elif col_id == "todo" and todo_special_count[0] == 1:
                todo_special_count[0] = 2
                people_options = "".join(f'<option{"" if p != who else " selected"}>{escape(p)}</option>' for p in AVATAR_COLORS.keys())
                html += f'<div class="kanban-task edit-mode" data-task-id="{t.get("id", "")}">'
                html += f'<div class="edit-row"><input type="text" value="{escape(t["title"])}" placeholder="Titre" style="font-weight:600"></div>'
                html += f'<div class="edit-row"><textarea placeholder="Detail">{escape(desc)}</textarea></div>'
                html += f'<div class="edit-row"><select>{people_options}</select><input type="text" value="{when_str}" placeholder="dd.mm" style="width:60px;flex:none"></div>'
                html += f'<div class="edit-actions"><button class="btn btn-save">Enregistrer</button><button class="btn btn-cancel">Annuler</button></div>'
                html += f'</div>'

            # Normal card
            else:
                html += f'<a class="kanban-task" href="#" style="text-decoration:none;color:inherit" data-task-id="{t.get("id", "")}">'
                html += f'<div class="task-body">'
                html += f'<div class="task-title">{escape(t["title"])}</div>'
                if desc:
                    html += f'<div class="task-desc">{desc}</div>'
                if project_names and "_project" in t:
                    pname, pcolor = t["_project"], t["_color"]
                    html += f'<div style="margin-top:2px"><span class="task-tag" style="background:{pcolor}">{escape(pname)}</span></div>'
                html += f'</div>'
                html += f'<div class="task-right">'
                html += f'<div class="task-avatar" style="background:{avatar_color}" title="{escape(who)}">{initials}</div>'
                if when_str:
                    html += f'<div class="task-when">{when_str}</div>'
                html += f'</div>'
                html += f'</a>'
        if hidden_count > 0:
            html += f'<div style="text-align:center;padding:6px;font-size:11px;color:var(--dimmed);cursor:pointer">+ {hidden_count} autres</div>'
        html += '</div></div>'
    if in_middle:
        html += '</div>'
    if in_rest:
        html += '</div>'
    html += '</div>'
    return html


# =====================================================================
# index.html — Dashboard
# =====================================================================
def build_header(prefix: str = "", current_cat: dict = None):
    """Shared header for all pages. prefix is the path to root ('' or '../')."""
    badge_html = ""
    for c in categories:
        count = len([p for p in projects if p["cat"] == c["id"]])
        is_active = current_cat and current_cat["id"] == c["id"]
        weight = "font-weight:800;" if is_active else ""
        badge_html += f'<a href="{prefix}cat/{c["id"]}.html" class="badge" style="background:color-mix(in srgb, {c["color"]} 12%, transparent);color:{c["color"]};text-decoration:none;{weight}">{escape(c["name"])} {count}</a>\n  '

    active_cat = current_cat if current_cat else categories[0]
    active_count = len([p for p in projects if p["cat"] == active_cat["id"]])
    return f'''<div class="header">
  <a href="{prefix}index.html" style="text-decoration:none"><h1>DASHBOARD</h1></a>
  <div class="header-badges">
    {badge_html}
  </div>
  <div class="header-badges-dropdown">
    <div class="badge-menu-toggle" onclick="this.parentElement.classList.toggle('open')">
      <span class="badge" style="background:color-mix(in srgb, {active_cat["color"]} 12%, transparent);color:{active_cat["color"]};text-decoration:none">{escape(active_cat["name"])} {active_count} <span class="badge-chevron">&#9662;</span></span>
    </div>
    <div class="badge-menu-dropdown">
      {badge_html}
    </div>
  </div>
  <span style="flex:1"></span>
  <div class="avatar-menu">
    <div class="avatar-btn" onclick="this.parentElement.classList.toggle('open')" style="width:28px;height:28px;border-radius:50%;background:#0969da;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:white;cursor:pointer" title="Q">Q</div>
    <div class="avatar-dropdown">
      <a href="#">Parametres</a>
      <a href="#">Deconnexion</a>
    </div>
  </div>
</div>'''


def build_index():
    header = build_header()

    # Category cards
    cat_section = '<div class="section"><div class="cat-grid">'
    for c in categories:
        cat_projects = [p for p in projects if p["cat"] == c["id"]]
        total_done = sum(p["done"] for p in cat_projects)
        total_tasks = sum(p["total"] for p in cat_projects)
        # Aggregate actual burndown
        if cat_projects:
            length = len(cat_projects[0]["actual"])
            agg_actual = [sum(p["actual"][i] for p in cat_projects) for i in range(length)]
        else:
            agg_actual = [0]

        project_list = ""
        for p in cat_projects:
            arrow, acolor = health_arrow(p)
            open_count = p["total"] - p["done"]
            doing_count = len([t for t in p["tasks"] if t["status"] == "doing"])
            if doing_count == 0:
                dot_color = "#d0d7de"
            else:
                dot_color = f'color-mix(in srgb, {c["color"]} {min(30 + doing_count * 20, 100)}%, white)'
            project_list += f'<div class="cat-project" onclick="window.location=\'cat/{c["id"]}.html#{p["id"]}\'"><span class="cat-project-dot" style="background:{dot_color}"></span><span class="cat-project-full">{escape(p["name"])}</span><span class="cat-project-short">{escape(p.get("acronym", p["name"][:3].upper()))}</span></div>'

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
  <div class="cat-projects">{project_list}</div>
</a>'''

    cat_section += '</div></div>'

    return page("Dashboard", header + cat_section)


# =====================================================================
# cat/{id}.html — Category kanban
# =====================================================================
def build_cat(cat: dict):
    cat_projects = [p for p in projects if p["cat"] == cat["id"]]
    total_done = sum(p["done"] for p in cat_projects)
    total_tasks = sum(p["total"] for p in cat_projects)

    header = build_header("../", current_cat=cat)

    body = ""
    for i, p in enumerate(cat_projects):
        arrow, acolor = health_arrow(p)
        open_count = p["total"] - p["done"]
        body += f'''<div class="section" id="{p["id"]}" style="padding-top:0">
  <div class="section-title">{escape(p.get("acronym", ""))} / {escape(p["name"])}</div>
{kanban_html(p["tasks"], show_edit=(i == 0))}
</div>'''

    return page(cat["name"], header + body, css_path="../style.css")




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

    print(f"\nDone: 1 index + {len(categories)} categories")


if __name__ == "__main__":
    main()
