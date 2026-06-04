---
id: 531
title: "KEN / Aide"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-30T09:36:32
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/pages
section_title: "Page templates (Jinja2)"
---

# #531 — KEN / Aide

La page /aide ne documente que le popup (Ctrl+Shift+K / Cmd+Shift+K) et parle encore d'une "capture d'écran optionnelle". Le mode annotation (#520, Alt+K / Option+K macOS) est complètement absent, et la capture est désormais textuelle (#514, pas de PNG).

(Tâche elle-même créée par le mode annotation depuis /aide — cf. blockquote dans la description originale.)

---

## Résolution

### Modifications
- src/dashboard/templates/aide.html :
  - **Sous-titre de la carte "Extension"** : remplacé "avec capture d'écran optionnelle" par "titre + URL + plan textuel de la page, ou surligner du texte sur la page et tout pousser en bloc" (reflète #514 + #520).
  - **Section 4** renommée "Capture rapide (popup)" : précise que le pré-remplissage inclut maintenant le plan h1–h3 + la sélection courante (capture textuelle structurée).
  - **Nouvelle section 5 "Annoter une page"** : raccourci `Alt+K` / `Option+K` macOS, badge `kb · 0`, mini-barre `🖍 Surligner`, persistance locale par URL canonique, drawer + Pousser sur kenboard, blockquotes + `[citer](…#:~:text=…)`, ESC pour fermer/sortir.

### Garde-fous
- tests/unit/test_page_routes.py::TestAidePage : 2 passed (rendu 200 + sections présentes inchangées).
---

[← retour à frontend/pages](index.md) · [voir log](../../log.md)
