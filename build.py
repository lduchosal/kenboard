#!/usr/bin/env python3
"""Generate static dashboard pages from data.json."""

import json
import os
from datetime import date
from html import escape
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(HERE, "data.json")) as f:
    data = json.load(f)

categories = data["categories"]
projects = data["projects"]

# -- Constants ----------------------------------------------------------------

COLUMNS = [
    ("todo", "A faire", "var(--todo)"),
    ("doing", "En cours", "var(--cyan)"),
    ("review", "Revue", "var(--purple)"),
    ("done", "Fait", "var(--green)"),
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

def burndown_bars(actual: list, color: str) -> str:
    mx = max(actual) if actual and max(actual) > 0 else 1
    return "".join(
        f'<div class="bar-group"><div style="height:{v/mx*100:.0f}%;background:{color};opacity:0.5;border-radius:1px"></div></div>'
        for v in actual
    )


def health_arrow(p: dict) -> tuple:
    li, la = p["ideal"][-1], p["actual"][-1]
    th = round(p["total"] * 0.2)
    if la <= li + 1: return ("↑", "var(--green)")
    if la <= li + th: return ("↗", "var(--orange)")
    return ("↓", "var(--red)")


def fmt_date(when_str: str) -> str:
    d = date.fromisoformat(when_str)
    return f'{d.day:02d}.{d.month:02d}'


def esc_attr(s: str) -> str:
    """Escape for use inside single-quoted HTML attributes."""
    return escape(s).replace("'", "&#39;")


# -- Shared modals & JS (included on every page) -----------------------------

def task_modal_html() -> str:
    who_options = "".join(f'<option>{escape(p)}</option>' for p in AVATAR_COLORS)
    return f'''<div class="project-add-modal" id="task-modal" style="display:none" onclick="this.style.display='none'">
  <div class="project-add-card" onclick="event.stopPropagation()">
    <button class="modal-close" onclick="this.closest('.project-add-modal').style.display='none'">&times;</button>
    <h3 id="task-modal-heading">Nouvelle t\u00e2che</h3>
    <div class="edit-row"><input type="text" id="task-modal-title" placeholder="Titre" style="font-weight:600"></div>
    <div class="edit-row"><textarea id="task-modal-desc" placeholder="Detail"></textarea></div>
    <div class="edit-row"><select id="task-modal-who">{who_options}</select><input type="text" id="task-modal-when" placeholder="dd.mm" style="width:60px;flex:none"><select id="task-modal-status"><option value="todo">A faire</option><option value="doing">En cours</option><option value="review">Revue</option><option value="done">Fait</option></select></div>
    <div class="edit-actions"><button class="btn btn-save" onclick="saveTaskModal()">Enregistrer</button><button class="btn btn-delete" id="task-modal-delete" style="display:none" onclick="confirmDelete(this, deleteTask)">Supprimer</button></div>
  </div>
</div>'''


def project_modal_html(cat_id: str = "") -> str:
    cat_val = f' value="{cat_id}"' if cat_id else ""
    return f'''<div class="project-add-modal" id="project-modal" style="display:none" onclick="this.style.display='none'">
  <div class="project-add-card" onclick="event.stopPropagation()">
    <button class="modal-close" onclick="this.closest('.project-add-modal').style.display='none'">&times;</button>
    <h3 id="proj-modal-title">Projet</h3>
    <div class="edit-row"><input type="text" id="new-proj-name" placeholder="Nom du projet" style="font-weight:600"></div>
    <div class="edit-row"><input type="text" id="new-proj-acronym" placeholder="ACRO" maxlength="4" style="width:60px;flex:none;text-transform:uppercase"><select id="new-proj-status"><option value="active">Actif</option><option value="archived">Archiv\u00e9</option></select></div>
    <input type="hidden" id="new-proj-cat"{cat_val}>
    <input type="hidden" id="new-proj-id">
    <div style="font-size:10px;font-weight:600;color:var(--dimmed);text-transform:uppercase;margin:8px 0 4px" id="proj-modal-projects-label">Projets</div>
    <div class="cat-modal-projects" id="proj-modal-projects"></div>
    <div class="edit-actions"><button class="btn btn-save" onclick="saveProject()">Enregistrer</button><button class="btn btn-delete" id="proj-modal-delete" style="display:none" onclick="confirmDelete(this, deleteProject)">Supprimer</button></div>
  </div>
</div>'''


def page(title: str, body: str, css_path: str = "style.css") -> str:
    js_path = css_path.replace("style.css", "app.js")
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
{task_modal_html()}
<div class="project-add-modal" id="confirm-modal" style="display:none" onclick="this.style.display='none'">
  <div class="project-add-card" onclick="event.stopPropagation()" style="width:280px">
    <h3 id="confirm-modal-title">Confirmer la suppression</h3>
    <div style="text-align:center;margin:16px 0">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none"><path d="M12 2L1 21h22L12 2z" fill="color-mix(in srgb, var(--red) 15%, white)" stroke="var(--red)" stroke-width="1.5" stroke-linejoin="round"/><path d="M12 9v5" stroke="var(--red)" stroke-width="2" stroke-linecap="round"/><circle cx="12" cy="17" r="1" fill="var(--red)"/></svg>
    </div>
    <p id="confirm-modal-msg" style="font-size:12px;color:var(--dimmed);margin-bottom:18px;text-align:center"></p>
    <div class="edit-actions" style="flex-direction:row;justify-content:flex-end">
      <button class="btn btn-cancel" onclick="document.getElementById('confirm-modal').style.display='none'">Annuler</button>
      <button class="btn btn-delete" id="confirm-modal-ok" onclick="">Supprimer</button>
    </div>
  </div>
</div>
<script defer src="{js_path}"></script>
</body>
</html>"""


# -- Kanban HTML --------------------------------------------------------------

def kanban_html(tasks: list) -> str:
    middle_cols = {"doing", "review"}
    rest_cols = {"doing", "review", "done"}
    html = '<div class="kanban">'
    in_rest = in_middle = False
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
            html += f'<button class="kanban-add-btn" onclick="openTaskModal(this.closest(\'.kanban-col\').querySelector(\'.kanban-tasks\'))">+</button>'
        html += '</div>'
        html += f'<div class="kanban-tasks" data-status="{col_id}">'

        max_visible = 5 if col_id == "done" else None
        hidden = max(0, len(col_tasks) - max_visible) if max_visible else 0

        for i, t in enumerate(col_tasks):
            is_hidden = max_visible and i >= max_visible
            who = t.get("who", "?")
            initials = who[0].upper()
            avatar_color = AVATAR_COLORS.get(who, "var(--dimmed)")
            when_str = fmt_date(t["when"]) if t.get("when") else ""
            desc = escape(t.get("desc", ""))

            hidden_cls = " task-hidden" if is_hidden else ""
            html += f'<div class="kanban-task{hidden_cls}" data-task-id="{t.get("id", "")}" onclick="toggleDetail(this)">'
            html += f'<div class="task-body"><div class="task-title">{escape(t["title"])}</div>'
            if desc:
                html += f'<div class="task-desc">{desc}</div>'
            html += '</div>'
            html += f'<div class="task-right"><div class="task-avatar" style="background:{avatar_color}" title="{escape(who)}">{initials}</div>'
            if when_str:
                html += f'<div class="task-when">{when_str}</div>'
            html += f'<button class="btn-edit detail-only" onclick="event.stopPropagation();openEditTask(\'{t.get("id","")}\',\'{esc_attr(t["title"])}\',\'{esc_attr(t.get("desc",""))}\',\'{escape(who)}\',\'{when_str}\',\'{t["status"]}\')">Editer</button>'
            html += '</div></div>'

        if col_id == "todo":
            html += '<div class="kanban-add-task" onclick="openTaskModal(this.closest(\'.kanban-col\').querySelector(\'.kanban-tasks\'))"><span style="font-size:18px">+</span> Ajouter une t&acirc;che</div>'
        if hidden > 0:
            html += f'<div class="show-more" onclick="this.parentElement.querySelectorAll(\'.task-hidden\').forEach(t=>t.classList.remove(\'task-hidden\'));this.remove()">+ {hidden} autres</div>'
        html += '</div></div>'

    if in_middle: html += '</div>'
    if in_rest: html += '</div>'
    html += '</div>'
    return html


# -- Header -------------------------------------------------------------------

def build_header(prefix: str = "", current_cat: dict = None) -> str:
    badge_html = ""
    for c in categories:
        count = len([p for p in projects if p["cat"] == c["id"]])
        active = current_cat and current_cat["id"] == c["id"]
        weight = "font-weight:800;" if active else ""
        badge_html += f'<a href="{prefix}cat/{c["id"]}.html" class="badge" style="background:color-mix(in srgb, {c["color"]} 12%, transparent);color:{c["color"]};text-decoration:none;{weight}">{escape(c["name"])} {count}</a>\n  '

    act = current_cat or categories[0]
    act_count = len([p for p in projects if p["cat"] == act["id"]])
    return f'''<div class="header">
  <a href="{prefix}index.html" style="text-decoration:none"><h1>DASHBOARD</h1></a>
  <div class="header-badges">{badge_html}</div>
  <div class="header-badges-dropdown">
    <div class="badge-menu-toggle" onclick="this.parentElement.classList.toggle('open')">
      <span class="badge" style="background:color-mix(in srgb, {act["color"]} 12%, transparent);color:{act["color"]};text-decoration:none">{escape(act["name"])} {act_count} <span class="badge-chevron">&#9662;</span></span>
    </div>
    <div class="badge-menu-dropdown">{badge_html}</div>
  </div>
  <span style="flex:1"></span>
  <div class="avatar-menu">
    <div class="avatar-btn" onclick="this.parentElement.classList.toggle('open')" style="width:28px;height:28px;border-radius:50%;background:var(--accent);display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:white;cursor:pointer" title="Q">Q</div>
    <div class="avatar-dropdown">
      <a href="#">Deconnexion</a>
    </div>
  </div>
</div>'''


def cat_projects_script() -> str:
    """Generate inline script with CAT_PROJECTS data for JS."""
    data = {
        c["id"]: [{"id": p["id"], "name": p["name"], "acronym": p.get("acronym", p["name"][:4].upper()), "tasks": len(p.get("tasks", []))} for p in projects if p["cat"] == c["id"]]
        for c in categories
    }
    return f'<script>const CAT_PROJECTS = {json.dumps(data)};</script>'


# -- Dashboard (index.html) --------------------------------------------------

def build_index():
    header = build_header()

    cat_section = '<div class="section"><div class="cat-grid">'
    for c in categories:
        cp = [p for p in projects if p["cat"] == c["id"]]
        total_done = sum(p["done"] for p in cp)
        total_tasks = sum(p["total"] for p in cp)
        agg_actual = [sum(p["actual"][i] for p in cp) for i in range(len(cp[0]["actual"]))] if cp else [0]

        project_list = ""
        for p in cp:
            doing = len([t for t in p["tasks"] if t["status"] == "doing"])
            dot_color = "#d0d7de" if doing == 0 else f'color-mix(in srgb, {c["color"]} {min(30 + doing * 20, 100)}%, white)'
            project_list += f'<div class="cat-project" onclick="event.preventDefault();window.location=\'cat/{c["id"]}.html#{p["id"]}\'"><span class="cat-project-dot" style="background:{dot_color}"></span><span class="cat-project-short">{escape(p.get("acronym", p["name"][:4].upper()))}</span></div>'

        cat_section += f'''<a class="cat-card" href="cat/{c["id"]}.html">
  <div class="cat-header">
    <div class="cat-dot" style="background:{c["color"]}"></div>
    <span class="cat-name">{escape(c["name"])}</span>
    <button class="btn-edit cat-edit-btn" onclick="event.preventDefault();editCat('{c["id"]}','{esc_attr(c["name"])}','{c["color"]}')">Editer</button>
    <div class="cat-kpis"><div class="cat-kpi">
      <div class="value" style="color:var(--text)">{total_tasks - total_done}</div>
      <div class="label">Ouvertes</div>
    </div></div>
  </div>
  <div class="cat-projects">{project_list}</div>
  <div class="cat-burndown">{burndown_bars(agg_actual, c["color"])}</div>
</a>'''

    cat_section += f'''<div class="cat-card cat-card-add" onclick="editCat('','','')">
  <span class="cat-add-plus"><span style="font-size:18px">+</span> Ajouter une cat\u00e9gorie</span>
</div>'''
    cat_section += '</div></div>'

    # Category edit modal
    color_dots = "".join(f'<span class="color-dot" data-color="{cv}" style="background:{cv}" onclick="event.stopPropagation();selectCatColor(this)"></span>' for cn, cv in COLOR_LIST)
    cat_modal = f'''<div class="project-add-modal" id="cat-modal" style="display:none" onclick="this.style.display='none'">
  <div class="project-add-card" onclick="event.stopPropagation()">
    <button class="modal-close" onclick="this.closest('.project-add-modal').style.display='none'">&times;</button>
    <h3>Editer la cat\u00e9gorie</h3>
    <div class="edit-row"><input type="text" id="cat-modal-name" placeholder="Nom de la categorie" style="font-weight:600;font-size:14px"></div>
    <div class="edit-row"><div class="color-field cat-modal-colors" id="cat-modal-colors">{color_dots}</div></div>
    <div style="font-size:10px;font-weight:600;color:var(--dimmed);text-transform:uppercase;margin:8px 0 4px">Projets</div>
    <div class="cat-modal-projects" id="cat-modal-projects"></div>
    <input type="hidden" id="cat-modal-id">
    <div class="edit-actions"><button class="btn btn-save" onclick="saveCat()">Enregistrer</button><button class="btn btn-delete" id="cat-modal-delete" style="display:none" onclick="confirmDelete(this, deleteCat)">Supprimer</button></div>
  </div>
</div>'''

    return page("Dashboard", header + cat_section + project_modal_html() + cat_modal + cat_projects_script())


# -- Category detail (cat/{id}.html) -----------------------------------------

def build_cat(cat: dict):
    cp = [p for p in projects if p["cat"] == cat["id"]]
    header = build_header("../", current_cat=cat)

    active_projects = [p for p in cp if p.get("status", "active") == "active"]
    archived_projects = [p for p in cp if p.get("status") == "archived"]

    body = ""
    for p in active_projects:
        body += f'''<div class="section" id="{p["id"]}" style="padding-top:0">
  <div class="section-title"><span>{escape(p.get("acronym", ""))} / {escape(p["name"])}</span><button class="btn-edit section-edit-btn" onclick="editProject('{p["id"]}','{esc_attr(p["name"])}','{esc_attr(p.get("acronym",""))}','{cat["id"]}','{p.get("status","active")}')">Editer</button></div>
{kanban_html(p["tasks"])}
</div>'''

    body += f'''<div class="section" style="padding-top:0">
  <div class="cat-card-add" onclick="document.getElementById('project-modal').style.display='flex'" style="border:2px dashed var(--border);border-radius:8px;padding:16px;text-align:center;cursor:pointer;color:var(--dimmed)">
    <span style="font-size:18px">+</span> Ajouter un projet
  </div>
</div>'''

    if archived_projects:
        body += f'''<div class="section" style="padding-top:0">
  <div class="archived-toggle" onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display==='none'?'block':'none';this.querySelector('span').textContent=this.nextElementSibling.style.display==='none'?'+':'-'">
    <span>+</span> Afficher les projets archiv\u00e9s ({len(archived_projects)})
  </div>
  <div class="archived-list" style="display:none">'''
        for p in archived_projects:
            body += f'''<div class="section archived-project" id="{p["id"]}" style="padding-top:0;opacity:0.5">
  <div class="section-title"><span>{escape(p.get("acronym", ""))} / {escape(p["name"])}</span><button class="btn-edit section-edit-btn" onclick="editProject('{p["id"]}','{esc_attr(p["name"])}','{esc_attr(p.get("acronym",""))}','{cat["id"]}','{p.get("status","active")}')">Editer</button></div>
{kanban_html(p["tasks"])}
</div>'''
        body += '</div></div>'

    return page(cat["name"], header + body + project_modal_html(cat["id"]) + cat_projects_script(), css_path="../style.css")


# -- HTML validation ----------------------------------------------------------

VOID_TAGS = {'br','hr','img','input','meta','link','area','base','col','embed','source','track','wbr'}

class TagChecker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack, self.errors = [], []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID_TAGS:
            self.stack.append((tag, self.getpos()))

    def handle_endtag(self, tag):
        if tag in VOID_TAGS: return
        if self.stack and self.stack[-1][0] == tag:
            self.stack.pop()
        else:
            expected = self.stack[-1][0] if self.stack else "none"
            self.errors.append(f"Line {self.getpos()[0]}: </{tag}> expected </{expected}>")


def validate_html(filepath: str) -> bool:
    with open(filepath) as f:
        checker = TagChecker()
        checker.feed(f.read())
    ok = not checker.errors and not checker.stack
    if checker.errors:
        for e in checker.errors[:5]: print(f"  ERROR {e}")
    if checker.stack:
        print(f"  UNCLOSED {[(t,l) for t,l in checker.stack[:5]]}")
    return ok


# -- Build all ----------------------------------------------------------------

def main():
    all_ok = True

    path = os.path.join(HERE, "index.html")
    with open(path, "w") as f:
        f.write(build_index())
    ok = validate_html(path)
    print(f"index.html {'OK' if ok else 'FAIL'}")
    all_ok = all_ok and ok

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
