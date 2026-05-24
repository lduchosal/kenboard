---
id: 176
title: "UI / IOS / Icon du lien"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:39
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/pages
section_title: "Page templates (Jinja2)"
---

# #176 — UI / IOS / Icon du lien

Quand on cree un lien du kenboard sur iOS pour qu il apparaisse avec les autres application, le lien n a pas de logo favico, analyse

---

## Resolution

L icone etait deja en place (apple-touch-icon.png 180x180 + link rel=apple-touch-icon dans base.html et login.html). Le probleme etait un cache iOS. Un refresh du lien sur l ecran d accueil a resolu le probleme. Aucune modification de code necessaire.
---

[← retour à frontend/pages](index.md) · [voir log](../../log.md)
