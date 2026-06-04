---
id: 567
title: "EXTENSION / paintbrush — skeleton viewport-only + couleurs de fond"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-30T23:07:46
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: extension
section_title: "Browser extension"
---

# #567 — EXTENSION / paintbrush — skeleton viewport-only + couleurs de fond

Suite de #564 : actuellement le squelette couvre toute la page scrollable (viewBox = documentWidth x documentHeight) et ignore les background-color.

---

## Résolution

### Modifications
extension/content/annotate.src.js :

**Viewport-only (skeleton)** :
- buildSkeletonSvg : viewport cull ajoutée — skip si rect.bottom <= 0 || rect.top >= innerHeight || rect.right <= 0 || rect.left >= innerWidth.
- Les éléments hors viewport au moment du push ne sont plus marshalés → SVG bien plus léger sur des pages longues.

**Viewport-only (viewBox)** :
- serialiseSvg : viewBox = `${scrollX} ${scrollY} ${innerWidth} ${innerHeight}` au lieu de toute la page. width display capé à 1600 mais aligné sur innerWidth.
- Le rect blanc de fond couvre désormais la zone viewport, pas tout le document.

**Couleurs de fond** :
- Helper isTransparentBg(bg) : retourne vrai pour "transparent", "rgba(*, *, *, 0)", vide.
- Pour chaque élément visible avec backgroundColor non transparent : émet un <rect fill="${bg}"> AVANT le texte/image-placeholder. L'ordre DOM (parents avant enfants) fait que les conteneurs colorés apparaissent en arrière-plan.

### Comportements obtenus
- Le SVG capturé = strictement ce qui est dans le viewport au moment où l'utilisateur appuie 'Pousser sur kenboard'.
- Les sections colorées de la page (hero, cards, navbar, boutons CTA…) gardent leurs couleurs computed (résolues par le navigateur, donc les variables CSS et autres sont déjà transformées en valeurs concrètes).
- Texte rendu avec font-size + color + font-family computed comme avant.
- Annotations rouges superposées aux bonnes coordonnées (page coords inchangées).

### Garde-fous
- bundle build : OK (30 KB).
- node --check + web-ext lint 0/0.
- vitest buildMarkdown : 6/6.
- NON testé navigateur — à valider sur une page colorée (ex. github.com) en regardant la fidélité du modal de tâche.
---

[← retour à extension](index.md) · [voir log](../log.md)
