---
id: 515
title: "EXTENSION / afficher la version dans la page de settings"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-29T22:26:46
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: extension
section_title: "Browser extension"
---

# #515 — EXTENSION / afficher la version dans la page de settings

Dans la page de configuration de l'extension (options.html), afficher la version courante (chrome.runtime.getManifest().version) pour savoir où l'on en est.

---

## Résolution

### Modifications
- extension/options.html — badge version `<span id="ext-version" class="ver">` à côté du titre H1 + style .ver (petit, gris/muet), façon header kenboard.
- extension/options.js — au DOMContentLoaded : `$("ext-version").textContent = \`v\${chrome.runtime.getManifest().version}\``.

### Comportements obtenus
- La page Réglages affiche « kenboard quick-task — Settings vX.Y.Z » ; on voit d'un coup d'œil la version installée (le manifest est synchronisé à la release par publish.sh).

### Garde-fous
- node --check extension/options.js : OK. web-ext lint : 0/0. extension/ hors périmètre Biome.
- NON testé en navigateur ici (getManifest() est une API runtime), mais l'appel est trivial et standard.
---

[← retour à extension](index.md) · [voir log](../log.md)
