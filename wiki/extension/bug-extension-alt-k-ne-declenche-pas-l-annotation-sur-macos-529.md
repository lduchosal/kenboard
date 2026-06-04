---
id: 529
title: "BUG / EXTENSION / Alt+K ne déclenche pas l'annotation sur macOS"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-30T01:09:22
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: extension
section_title: "Browser extension"
---

# #529 — BUG / EXTENSION / Alt+K ne déclenche pas l'annotation sur macOS

Sur macOS, Option+K injecte le caractère mort '˚' donc e.key === 'k' était toujours faux dans onKeyDown. Le mode annotation #520 ne s'activait jamais. Symptôme : "Alt+K ne fait rien apparaitre" (signalé en testant la 0.1.117).

---

## Résolution

### Modifications
- extension/content/annotate.src.js — onKeyDown utilise désormais `e.altKey && e.code === 'KeyK'` (touche physique) au lieu de `e.key === 'k'` (caractère injecté par la layout/OS).
- bootstrap() ajoute `console.info('[kenboard:annotate] loaded — Alt+K to activate')` : marqueur visible dans la DevTools console pour confirmer que le content script a bien été injecté (utile pour diagnostiquer pages privilégiées, blocages CSP, etc.).
- catches silencieux remplacés par des `console.warn` ciblés (re-anchor au load, anchoring à la création) — plus de fail silencieux à l'avenir.

### Garde-fous
- pdm run build-extension : OK (rebuilt).
- node --check bundle : OK.
- web-ext lint : 0/0.
- Le fix est inclus dans la prochaine release (0.1.118).
---

[← retour à extension](index.md) · [voir log](../log.md)
