---
id: 556
title: "BUG / EXTENSION / paintbrush — le badge est inclickable en mode dessin (z-index overflow)"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-30T16:33:18
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: extension
section_title: "Browser extension"
---

# #556 — BUG / EXTENSION / paintbrush — le badge est inclickable en mode dessin (z-index overflow)

Quand le mode paintbrush est on, la capture pane (transparente, plein viewport pour drag-to-draw) couvre le badge et l'empêche de recevoir les clics → impossible d'ouvrir le drawer → impossible de pousser sur kenboard.

Cause : le SHADOW_CSS template utilisait `z-index: ${Z+1}` = 2147483648 qui dépasse la limite 32 bits du z-index CSS et tombe sur la valeur par défaut, donc badge/palette/drawer/composer se retrouvaient en-dessous de la capture pane (z-index Z = 2147483647).

---

## Résolution

### Modifications
- extension/content/annotate.src.js : remplacement de la constante unique Z par un échelon explicite et borné sous INT32_MAX :
  - Z_SVG       = 2147483630 (overlay SVG, pointer-events: none)
  - Z_CAPTURE   = 2147483631 (pane drag-to-draw)
  - Z_UI        = 2147483640 (badge, palette)
  - Z_DRAWER    = 2147483645 (drawer slide-in)
  - Z_COMPOSER  = 2147483646 (composer texte + host)
- Du coup les éléments d'UI sont peints AU-DESSUS de la capture pane et reçoivent les clics correctement.

### Garde-fous
- bundle build : OK.
- node --check : OK.
- web-ext lint : 0/0.
- NON testé en navigateur ici — à valider en cliquant le badge en mode paintbrush.
---

[← retour à extension](index.md) · [voir log](../log/2026-05-30.md)
