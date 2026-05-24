---
id: 148
title: "CLI / WIN / Encoding UTF8"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:38
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: cli/ken
section_title: "ken task CLI"
---

# #148 — CLI / WIN / Encoding UTF8

Le CLI ken sous windows plante à cause des encoding.
Certains caractères UTF8 font planter le cli: -> etc..
il faut préfixer toutes les commandes ken avec PYTHONUTF8=1 c'est pas super. Peux-tu contrôler ce problème

---

## Résolution

### Cause

Windows utilise `cp1252` (ou la locale système) comme encodage par défaut pour `stdout`/`stderr`. Les caractères UTF-8 courants dans les descriptions de tâches (→, accents, émojis) provoquent un `UnicodeEncodeError` au moment de l'affichage.

### Fix

Les deux points d'entrée CLI (`ken.py` et `cli.py`) appellent `sys.stdout.reconfigure(encoding="utf-8")` au chargement du module, avant que Click n'écrive quoi que ce soit. Le fix ne s'active que sur `sys.platform == "win32"` — aucun impact sur Linux/macOS/FreeBSD.

L'utilisateur Windows n'a plus besoin de `PYTHONUTF8=1` : c'est plug-and-play après `pip install kenboard`.

### Garde-fous

- 265 tests verts, `pdm run check` OK
- Aucun changement sur les plateformes non-Windows (`# pragma: no cover` sur le bloc win32)
---

[← retour à cli/ken](index.md) · [voir log](../../log.md)
