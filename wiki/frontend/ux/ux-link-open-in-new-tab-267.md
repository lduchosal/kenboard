---
id: 267
title: "UX / Link / Open in new tab"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:55
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/ux
section_title: "UX / interactions"
---

# #267 — UX / Link / Open in new tab

## Demande

Tous les liens dans les descriptions d'une tâche doivent être ouverts dans un nouvel onglet pour ne pas perdre le travail dans ken.

---

## Résolution

### Modifications

- `src/dashboard/static/js/markdown.js` : nouvelle fonction `_ensureLinkOpensNewTab()` qui enregistre un hook `afterSanitizeAttributes` sur DOMPurify. Le hook ajoute `target=\"_blank\"` et `rel=\"noopener noreferrer\"` à chaque `<a>` sanitisé. Lazy + idempotent (marker `DOMPurify._kenboardLinkHook` sur l'instance pour éviter la double registration). Appelé en début de `renderMarkdown` plutôt qu'au module-load pour permettre aux mocks de tests de se setup en `beforeEach`. Garde-fou supplémentaire si `DOMPurify.addHook` n'existe pas (mock shim minimal dans `detail.test.js`).
- `src/dashboard/static/js/markdown.test.js` :
  - Mock DOMPurify amélioré : implémente `addHook` + `sanitize` qui parcourt les éléments et applique les hooks enregistrés.
  - Mock `marked.parse` étendu : substitue `[text](url)` → `<a href=\"url\">text</a>` minimaliste pour exercer le path link end-to-end.
  - Nouveau test : `[click](https://example.com)` doit produire un `<a target=\"_blank\" rel=\"noopener noreferrer\" href=\"https://example.com\">`.

### Pourquoi DOMPurify hook plutôt que le marked renderer

- Couvre les trois sources de liens uniformément : markdown `[text](url)`, autolinks `<https://...>`, HTML brut `<a href>`.
- Tourne après la sanitisation, donc l'URL est déjà validée par DOMPurify (XSS, javascript:, etc.).
- Une seule registration sur l'objet DOMPurify global → s'applique partout où on appelle `DOMPurify.sanitize` (cards via `markdown.js` ET fullscreen via `fullscreen.js`).

### Comportements obtenus

- `[click](https://example.com)` dans une description rend `<a href=\"https://example.com\" target=\"_blank\" rel=\"noopener noreferrer\">click</a>`.
- Idem pour les autolinks (`<https://example.com>`) et le HTML brut tel que `<a href=\"...\">...</a>`.
- Idem dans la vue plein écran (`#fs-desc`) qui passe par le même DOMPurify.
- Aucune fuite de `window.opener` / `Referer` vers la nouvelle page (`rel=noopener noreferrer`).

### Garde-fous

- `pdm run js-test` : 61 passed (60 existants + 1 nouveau)
- `pdm run check` (composite Python + JS) : 385 passed
- `pdm run test-e2e` : 52 passed / 0 failed
- Bundle : ~23 KB / ~6 KB gzip
---

[← retour à frontend/ux](index.md) · [voir log](../../log/2026-05-24.md)
