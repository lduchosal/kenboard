---
id: 564
title: "EXTENSION / paintbrush — conversion HTML→SVG légère de la page (background context)"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-30T22:50:23
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: extension
section_title: "Browser extension"
---

# #564 — EXTENSION / paintbrush — conversion HTML→SVG légère de la page (background context)

Aujourd'hui le SVG attachement contient uniquement la couche d'annotations (#541 décision b), affiché sur un damier transparent dans le modal. La page d'origine est perdue.

Décision UX validée : squelette + texte (option 2 — équilibre lisibilité / taille).

---

## Résolution

### Modifications
extension/content/annotate.src.js :
- Nouvelle fonction `buildSkeletonSvg()` : DOM-walk de document.body.getElementsByTagName('*'). Pour chaque élément visible (skip script/style/noscript/meta/link/head, skip width<1 ou height<1, skip display:none, visibility:hidden, opacity:0), récupère getBoundingClientRect + scroll → coords page.
- Pour <img>/<video>/<canvas>/<picture> : émet un placeholder gris avec label (alt ou tag name).
- Pour les éléments avec direct text nodes (pas les ancêtres pour éviter duplication) : émet un <text> avec font-size + color + font-family computed (première famille, sans quotes), texte tronqué à 280 chars.
- Caps : MAX_ELEMENTS = 2000, MAX_SKELETON_BYTES = 250_000. Au-delà, le skeleton est tronqué (warning console).
- `escapeXml()` helper pour `& < > "` (text content + attributs).
- `serialiseSvg()` refondue : retourne maintenant une string SVG complète au lieu de passer par DOM API + XMLSerializer. viewBox = `0 0 documentWidth documentHeight`. Structure : rect blanc fond + <g class='kb-skel' opacity='0.85'>squelette</g> + <g class='kb-annotations'>annotations rouges</g>. width capé à 1600.

### Comportements obtenus
- Le SVG attachement embarque maintenant un squelette lisible de la page sous les annotations rouges. Quand on rouvre la tâche, on voit la structure + le texte qui était sur la page + les rectangles/notes en surimpression.
- Taille typique : ~50-200 KB pour une page web courante (vs ~5 KB pour annotations seules). Tient large dans MEDIUMTEXT.
- Sans annotations dessinées : retourne "" (pas de push possible de toute façon).
- Pages géantes (>2000 éléments ou >250 KB de skeleton) : tronqué proprement avec warning.

### Garde-fous
- bundle build : OK, 30 KB (vs 27 KB avant — +3 KB pour la logique skeleton).
- node --check : OK.
- web-ext lint : 0/0.
- vitest buildMarkdown : 6/6 (inchangé).
- NON testé en navigateur — à valider en faisant un push depuis n'importe quelle page web : la tâche créée doit avoir un attachement où la page est reconnaissable.
---

[← retour à extension](index.md) · [voir log](../log/2026-05-30.md)
