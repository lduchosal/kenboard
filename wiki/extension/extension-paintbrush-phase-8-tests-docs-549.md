---
id: 549
title: "EXTENSION / paintbrush - phase 8 tests + docs"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-31T00:15:45
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: extension
section_title: "Browser extension"
---

# #549 — EXTENSION / paintbrush - phase 8 tests + docs

Phase 8 cleanup + tests + docs du paintbrush (Epic #541). Consolidait ce qui restait de #548.

---

## Résolution

### Cleanup deps
- `npm uninstall dom-anchor-text-quote dom-anchor-text-position` — devDependencies retirées de package.json. Bundle déjà passé de 113 KB à 30 KB depuis la réécriture en mode paintbrush ; les libs n'étaient plus importées, juste dans le manifest npm.

### Extraction module pour testabilité
- `extension/content/paintbrushSvg.js` (nouveau) — module pur exportant `escapeXml`, `serialiseSvg`, `RED`, `RECT_STROKE`, `TEXT_SIZE`, `SVG_NS`. Pas de dépendance runtime navigateur.
- `extension/content/annotate.src.js` — importe les helpers depuis paintbrushSvg.js, garde uniquement le wrapper `serialiseSvg()` qui capture window.scroll/inner puis délègue à `serialiseSvgPure`.

### Tests
- `extension/content/paintbrushSvg.test.js` (nouveau) — 8 tests vitest :
  - escapeXml : 4 chars + coercion non-string.
  - serialiseSvg : empty shapes → "", viewBox sur viewport, rectangle rouge 5px stroke transparent fill, texte avec échappement XML, groupe skeleton inclus quand fourni, width cap 1600 sur viewport très large.

### Docs
- `extension/README.md` section "Annotate a page" : réécriture pour le paintbrush — Alt+P, palette Rectangle/Texte, hit-test sous rectangle, drawer, push avec SVG attaché. Mention du z-index ordering (badge/palette/drawer au-dessus de la capture pane).
- `src/dashboard/templates/aide.html` section 5 : pareil — Alt+P (Option+P macOS), palette, capture du texte sous rectangle, SVG attaché visible sur le modal détail.

### Garde-fous
- pdm run build-extension : OK (bundle 31 KB).
- node --check : OK.
- pdm run js-test : 77/77 (69 existants + 8 nouveaux paintbrushSvg).
- /aide rendu côté serveur (TestAidePage) : 2/2.
---

[← retour à extension](index.md) · [voir log](../log.md)
