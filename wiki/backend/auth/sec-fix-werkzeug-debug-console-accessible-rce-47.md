---
id: 47
title: "SEC / FIX / Werkzeug debug console accessible (RCE)"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:18
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #47 — SEC / FIX / Werkzeug debug console accessible (RCE)

**Sévérité: CRITICAL**

`kenboard serve --debug` expose la console interactive Werkzeug sur `/console`. Permet l'exécution de code Python arbitraire (RCE) sur le serveur. Le PIN est dérivé d'infos potentiellement énumérables ("Werkzeug Debugger PIN bypass", CVE historique). Avec `WERKZEUG_DEBUG_PIN=off`, c'est full RCE direct.

**Reproduction:** `python pentest/debug_console.py` (nécessite `kenboard serve --port 5056 --debug`)

**Remédiation:**
- `kenboard serve --debug` ne devrait JAMAIS être exposé à autre chose que 127.0.0.1. Forcer `--host 127.0.0.1` quand `--debug` est passé.
- Documenter dans CLAUDE.md / INSTALL.md: "--debug est local-only".
- En prod, utiliser gunicorn/uwsgi (déjà recommandé).
---

[← retour à backend/auth](index.md) · [voir log](../../log/2026-05-24.md)
