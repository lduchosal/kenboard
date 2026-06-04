---
id: 502
title: "EXTENSION / Icon"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-29T08:13:05
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: extension
section_title: "Browser extension"
---

# #502 — EXTENSION / Icon

Utiliser l'icon du kenboard pour l'icon de l'extension

---

## Résolution

### Modifications
- extension/icons/icon-{16,32,48,128}.png — rendus depuis src/dashboard/static/logo.svg (pixel-art 32x32, crispEdges) via rsvg-convert.
- extension/manifest.json — ajout du bloc top-level "icons" (16/32/48/128) et de action.default_icon (16/32). Le bloc "icons" sert la barre d'outils, la page about:addons / chrome://extensions et le store ; default_icon sert le bouton de la toolbar.

### Comportements obtenus
- L'extension affiche désormais le logo kenboard dans la barre d'outils du navigateur et dans la liste des extensions (Chrome/Edge/Brave/Firefox), au lieu de l'icône puzzle générique.
- Les PNG sont committés dans extension/ donc inclus automatiquement dans le zip de release (publish.sh fait `cd extension && zip -r`).

### Garde-fous
- manifest.json revalidé en JSON (python json.load) — OK.
- Signatures PNG vérifiées (file): 16x16/32x32/48x48/128x128 RGB non-interlaced.
- Régénération : `for s in 16 32 48 128; do rsvg-convert -w $s -h $s src/dashboard/static/logo.svg -o extension/icons/icon-$s.png; done`
---

[← retour à extension](index.md) · [voir log](../log.md)
