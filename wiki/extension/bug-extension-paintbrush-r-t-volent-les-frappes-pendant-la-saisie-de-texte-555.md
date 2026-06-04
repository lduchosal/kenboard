---
id: 555
title: "BUG / EXTENSION / paintbrush — R/T volent les frappes pendant la saisie de texte"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-30T16:27:28
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: extension
section_title: "Browser extension"
---

# #555 — BUG / EXTENSION / paintbrush — R/T volent les frappes pendant la saisie de texte

En mode texte, taper T ou R dans le composer déclenche le switch d'outil au lieu d'écrire le caractère. Conséquence : impossible de saisir un mot contenant T ou R dans une annotation.

Cause : document.activeElement renvoie le **host Shadow DOM** (un <div>) quand le focus est dans le shadow, donc le garde 'activeElement.tagName !== INPUT' ne couvre pas l'input du composer.

---

## Résolution

### Modifications
- extension/content/annotate.src.js : nouvelle fonction `isTyping()` qui retourne vrai si :
  1. `composerEl.classList.contains("on")` — le composer paintbrush est visible.
  2. `shadow.activeElement.tagName === "INPUT" | "TEXTAREA"` — focus dans notre shadow (cas principal du bug).
  3. `document.activeElement.tagName === "INPUT" | "TEXTAREA"` ou `isContentEditable === true` — focus dans un champ normal de la page.
- onKeyDown gate maintenant les raccourcis R/T sur `!isTyping()`.

### Garde-fous
- bundle build : OK.
- node --check : OK.
- web-ext lint : 0/0.
- NON testé en navigateur ici. À valider en tapant un mot avec T/R dans le composer paintbrush.
---

[← retour à extension](index.md) · [voir log](../log.md)
