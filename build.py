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


FIRST_COLOR = "var(--orange)"

COLOR_LIST = [
    ("Orange", "var(--orange)", "\U0001f7e0"),
    ("Vert", "var(--green)", "\U0001f7e2"),
    ("Bleu", "var(--accent)", "\U0001f535"),
    ("Violet", "var(--purple)", "\U0001f7e3"),
    ("Cyan", "var(--cyan)", "\U0001f539"),
    ("Rouge", "var(--red)", "\U0001f534"),
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

// Edit category modal
function editCat(id, name, color) {{
  const modal = document.getElementById('cat-modal');
  if (!modal) return;
  document.getElementById('cat-modal-id').value = id;
  document.getElementById('cat-modal-name').value = name;
  document.querySelector('#cat-modal h3').textContent = id ? 'Editer categorie' : 'Nouvelle categorie';
  const colors = document.getElementById('cat-modal-colors');
  colors.querySelectorAll('.color-dot').forEach(d => {{
    d.classList.toggle('selected', d.dataset.color === color);
  }});
  modal.style.display = 'flex';
}}

function selectCatColor(dot) {{
  const container = document.getElementById('cat-modal-colors');
  container.querySelectorAll('.color-dot').forEach(d => d.classList.remove('selected'));
  dot.classList.add('selected');
}}

function saveCat() {{
  const id = document.getElementById('cat-modal-id').value;
  const name = document.getElementById('cat-modal-name').value.trim();
  const selected = document.querySelector('#cat-modal-colors .color-dot.selected');
  const color = selected ? selected.dataset.color : '';
  if (!name) return;
  const method = id ? 'PATCH' : 'POST';
  const url = id ? `${{API_BASE}}/categories/${{id}}` : `${{API_BASE}}/categories`;
  fetch(url, {{
    method,
    headers: {{ 'Content-Type': 'application/json' }},
    body: JSON.stringify({{ name, color }})
  }}).then(() => window.location.reload())
    .catch(err => console.warn('API not available:', err));
  document.getElementById('cat-modal').style.display = 'none';
}}

// Edit / Add project
function editProject(id, name, acronym, due, cat) {{
  const modal = document.getElementById('project-modal');
  if (!modal) return;
  document.getElementById('proj-modal-title').textContent = id ? 'Editer projet' : 'Nouveau projet';
  document.getElementById('new-proj-id').value = id || '';
  document.getElementById('new-proj-cat').value = cat || '';
  document.getElementById('new-proj-name').value = name || '';
  document.getElementById('new-proj-acronym').value = acronym || '';
  document.getElementById('new-proj-due').value = due || '';
  modal.style.display = 'flex';
}}

function saveProject() {{
  const id = document.getElementById('new-proj-id').value;
  const name = document.getElementById('new-proj-name').value.trim();
  const acronym = document.getElementById('new-proj-acronym').value.trim().toUpperCase();
  const due = document.getElementById('new-proj-due').value.trim();
  const cat = document.getElementById('new-proj-cat').value;
  if (!name || !acronym) return;
  const method = id ? 'PATCH' : 'POST';
  const url = id ? `${{API_BASE}}/projects/${{id}}` : `${{API_BASE}}/projects`;
  fetch(url, {{
    method,
    headers: {{ 'Content-Type': 'application/json' }},
    body: JSON.stringify({{ name, acronym, cat, due }})
  }}).then(() => window.location.reload())
    .catch(err => console.warn('API not available:', err));
  document.getElementById('project-modal').style.display = 'none';
}}

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

// Drag & drop
const API_BASE = '/api/v1';

// Category drag & drop
const catGrid = document.querySelector('.cat-grid');
if (catGrid) {{
  new Sortable(catGrid, {{
    animation: 150,
    draggable: '.cat-card:not(.cat-card-add)',
    ghostClass: 'task-ghost',
    chosenClass: 'task-chosen',
    filter: '.cat-card-add:not(.editing)',
    onEnd: (evt) => {{
      fetch(`${{API_BASE}}/categories/reorder`, {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ from: evt.oldIndex, to: evt.newIndex }})
      }}).catch(err => console.warn('API not available:', err));
    }}
  }});
}}

// Kanban drag & drop

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
    for ci, c in enumerate(categories):
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
            project_list += f'<div class="cat-project" onclick="event.preventDefault();window.location=\'cat/{c["id"]}.html#{p["id"]}\'"><span class="cat-project-dot" style="background:{dot_color}"></span><span class="cat-project-full">{escape(p["name"])}</span><span class="cat-project-short">{escape(p.get("acronym", p["name"][:4].upper()))}</span></div>'

        cat_section += f'''<a class="cat-card" href="cat/{c["id"]}.html">
  <div class="cat-header">
    <div class="cat-dot" style="background:{c["color"]}"></div>
    <span class="cat-name">{escape(c["name"])}</span>
    <button class="btn-edit cat-edit-btn" onclick="event.preventDefault();editCat('{c["id"]}','{escape(c["name"])}','{c["color"]}')">Editer</button>
    <div class="cat-kpis"><div class="cat-kpi">
      <div class="value" style="color:var(--text)">{total_tasks - total_done}</div>
      <div class="label">Ouvertes</div>
    </div></div>
  </div>
  <div class="cat-projects">{project_list}</div>
  <div class="cat-burndown">{burndown_bars(agg_actual, c["color"])}</div>
</a>'''

    # Add category button
    cat_section += f'''<div class="cat-card cat-card-add" onclick="editCat('','','')">
  <span class="cat-add-plus">+</span>
</div>'''

    cat_section += '</div></div>'

    # Project edit modal
    modal = '''<div class="project-add-modal" id="project-modal" style="display:none" onclick="this.style.display='none'">
  <div class="project-add-card" onclick="event.stopPropagation()">
    <h3 id="proj-modal-title">Projet</h3>
    <div class="edit-row"><input type="text" id="new-proj-name" placeholder="Nom du projet" style="font-weight:600"></div>
    <div class="edit-row"><input type="text" id="new-proj-acronym" placeholder="ACR" maxlength="4" style="width:60px;flex:none;text-transform:uppercase"><input type="text" id="new-proj-due" placeholder="dd.mm" style="width:60px;flex:none"></div>
    <input type="hidden" id="new-proj-cat">
    <input type="hidden" id="new-proj-id">
    <div class="edit-actions"><button class="btn btn-save" onclick="saveProject()">Enregistrer</button><button class="btn btn-cancel" onclick="document.getElementById(\'project-modal\').style.display=\'none\'">Annuler</button></div>
  </div>
</div>'''

    # Category edit modal
    cat_color_dots = "".join(f'<span class="color-dot" data-color="{cv}" style="background:{cv}" onclick="event.stopPropagation();selectCatColor(this)"></span>' for cn, cv, dot in COLOR_LIST)
    cat_modal = f'''<div class="project-add-modal" id="cat-modal" style="display:none" onclick="this.style.display='none'">
  <div class="project-add-card" onclick="event.stopPropagation()">
    <h3>Editer categorie</h3>
    <div class="edit-row"><input type="text" id="cat-modal-name" placeholder="Nom de la categorie" style="font-weight:600;font-size:14px"></div>
    <div class="edit-row"><div class="color-field cat-modal-colors" id="cat-modal-colors">{cat_color_dots}</div></div>
    <input type="hidden" id="cat-modal-id">
    <div class="edit-actions"><button class="btn btn-save" onclick="saveCat()">Enregistrer</button><button class="btn btn-cancel" onclick="document.getElementById('cat-modal').style.display='none'">Annuler</button></div>
  </div>
</div>'''

    return page("Dashboard", header + cat_section + modal + cat_modal)


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
# HTML validation
# =====================================================================
from html.parser import HTMLParser

VOID_TAGS = {'br','hr','img','input','meta','link','area','base','col','embed','source','track','wbr'}

class TagChecker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID_TAGS:
            self.stack.append((tag, self.getpos()))

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        if self.stack and self.stack[-1][0] == tag:
            self.stack.pop()
        else:
            expected = self.stack[-1][0] if self.stack else "none"
            self.errors.append(f"Line {self.getpos()[0]}: </{tag}> but expected </{expected}>")


def validate_html(filepath: str) -> bool:
    with open(filepath) as f:
        content = f.read()
    checker = TagChecker()
    checker.feed(content)
    ok = True
    if checker.errors:
        ok = False
        for e in checker.errors[:5]:
            print(f"  ERROR {e}")
    if checker.stack:
        ok = False
        unclosed = [(t, l) for t, l in checker.stack]
        print(f"  UNCLOSED {unclosed[:5]}")
    return ok


# =====================================================================
# Build all
# =====================================================================
def main():
    all_ok = True

    # index
    path = os.path.join(HERE, "index.html")
    with open(path, "w") as f:
        f.write(build_index())
    ok = validate_html(path)
    print(f"index.html {'OK' if ok else 'FAIL'}")
    all_ok = all_ok and ok

    # categories
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
        print("WARNING: HTML validation errors detected!")
        exit(1)


if __name__ == "__main__":
    main()
