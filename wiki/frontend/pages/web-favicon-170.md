---
id: 170
title: "WEB / FAVICON"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:51
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/pages
section_title: "Page templates (Jinja2)"
---

# #170 — WEB / FAVICON

Quand on cree un raccourci du kenboard sur son écran d'accueil ios l icon du kenboard n'est pas défini et ne représente pas la direction artistique du projet

---

## Résolution

- Généré depuis `logo.svg` via cairosvg + Pillow : `favicon.ico` (16/32/48), `favicon-32.png` (32×32), `apple-touch-icon.png` (180×180)
- Ajout des `<link rel="icon">` et `<link rel="apple-touch-icon">` dans `base.html` et `login.html`
- L'icône iOS reprend le logo KEN pixel-art sur fond blanc
---

[← retour à frontend/pages](index.md) · [voir log](../../log.md)
