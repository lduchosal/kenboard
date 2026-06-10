"""Stylesheet embedded in every page rendered by ``ken wiki build``.

Split out of ``wiki_build.py`` (ken #806) — pure data, no logic. Mirrors the board
templates (``.fullscreen-card`` etc., #376f) at a high level.
"""

_WIKI_HTML_CSS = """\
body{margin:0;font-family:system-ui,sans-serif;color:#222;background:#fff}
.layout{display:grid;grid-template-columns:240px 1fr;min-height:100vh}
nav.sidebar{background:#f6f8fa;border-right:1px solid #d0d7de;padding:16px;
  overflow-y:auto;font-size:13px}
nav.sidebar h1{font-size:14px;text-transform:uppercase;color:#57606a;margin:0 0 12px}
nav.sidebar ul{list-style:none;padding:0;margin:0}
nav.sidebar li{margin:2px 0}
nav.sidebar a{color:#0969da;text-decoration:none}
nav.sidebar a:hover{text-decoration:underline}
nav.sidebar a.current{font-weight:600;color:#1a1a1a}
main{padding:24px 32px;max-width:900px}
main h1{margin-top:0}
main code{background:#f6f8fa;padding:1px 4px;border-radius:3px;font-size:90%}
main pre{background:#f6f8fa;padding:12px;border-radius:6px;overflow-x:auto}
main pre code{background:transparent;padding:0}
main a{color:#0969da}
/* Task detail (#376f — mirrors templates/modals/task_fullscreen.html) */
.fullscreen-card{background:#fff;border:1px solid #d0d7de;border-radius:10px;
  padding:32px 36px;max-width:760px}
.fullscreen-header{display:flex;align-items:center;gap:12px;margin-bottom:12px}
.fullscreen-id{font-size:12px;color:#57606a;font-weight:600}
.fullscreen-status{font-size:11px;text-transform:uppercase;letter-spacing:.5px;
  color:#57606a;background:#f6f8fa;padding:3px 8px;border-radius:10px}
.fullscreen-status.status-todo{background:#ddf4ff;color:#0969da}
.fullscreen-status.status-doing{background:#fff8c5;color:#9a6700}
.fullscreen-status.status-review{background:#dafbe1;color:#1a7f37}
.fullscreen-status.status-done{background:#eaeef2;color:#57606a}
.fullscreen-title{font-size:22px;font-weight:700;margin:0 0 16px;line-height:1.3}
.fullscreen-meta{display:flex;align-items:center;gap:10px;margin-bottom:20px;
  font-size:13px;color:#57606a}
.task-avatar{width:28px;height:28px;border-radius:50%;display:flex;
  align-items:center;justify-content:center;color:#fff;font-weight:700;font-size:12px}
.fs-who{font-weight:600;color:#222}
.fullscreen-desc{font-size:14px;line-height:1.7;border-top:1px solid #d0d7de;
  padding-top:16px}
.fullscreen-desc h1,.fullscreen-desc h2,.fullscreen-desc h3{margin-top:16px;
  margin-bottom:8px}
.fullscreen-desc pre{background:#f6f8fa;border-radius:4px;padding:12px;
  overflow-x:auto;font-size:12px}
.fullscreen-desc code{background:#f6f8fa;border-radius:3px;padding:1px 4px;font-size:12px}
.fullscreen-desc pre code{background:transparent;padding:0}
.fullscreen-desc ul,.fullscreen-desc ol{padding-left:20px}
.wiki-nav{margin-top:20px;padding-top:12px;border-top:1px solid #d0d7de;
  font-size:13px;color:#57606a}
.wiki-nav a{color:#0969da}
/* Build footer (#743) — version of ``ken`` + generation timestamp. */
.wiki-footer{margin-top:40px;padding-top:12px;border-top:1px solid #d0d7de;
  font-size:11px;color:#57606a;text-align:right}
"""
