---
id: 15
title: "UI / UX / le texte d'une tache se render en MD"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:07
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/ux
section_title: "UX / interactions"
---

# #15 — UI / UX / le texte d'une tache se render en MD

Le texte d'une tache est rédigé en MD markdown. L'affichage dans l'UI doit être rendu selon le format MD attendu.

## Choix de la lib : marked.js

- Lib la plus standard de l'écosystème (markedjs/marked, MIT, ~17M dl/semaine)
- Single file ~35 KB, pas de build, pas de dépendance — vendoré dans `static/marked.min.js` (v12.0.2) sur le même modèle que `sortable.min.js`
- Alternatives écartées : markdown-it (plus gros), micromark (API + bas niveau), showdown (moins maintenu)

## Implémentation

- `templates/base.html` : ajout du `<script src="marked.min.js">`
- `app.js` : `renderMarkdown()` parcourt tous les `.task-desc`, lit `textContent` (le markdown raw, échappé par Jinja → restitué tel quel par textContent), parse via `marked.parse()` avec `gfm:true, breaks:true`, injecte en `innerHTML`, marque `data-md-rendered=1` pour ne pas re-parser
- La textarea du modal d'édition continue à recevoir le markdown raw via `desc | jsesc` — l'édition n'est donc pas affectée
- `style.css` : règles pour `.task-desc p / h / ul / ol / code / pre / blockquote / a`. La règle `white-space: pre-wrap` du detail-mode est passée à `normal` pour ne pas dupliquer les sauts de ligne entre HTML et CSS

## Sécurité

Marked v12 ne sanitize plus (option `sanitize` retirée). Pour un outil interne avec auth à venir, on accepte le risque de HTML brut dans les descriptions. Si besoin plus tard : DOMPurify côté client ou bleach côté serveur.

## Tests

- 64 unit tests OK
- 23 e2e tests OK (le `to_have_text("Nouvelle description")` reste valide car Playwright normalise le whitespace, et `<p>Nouvelle description</p>` a le bon textContent)
---

[← retour à frontend/ux](index.md) · [voir log](../../log.md)
