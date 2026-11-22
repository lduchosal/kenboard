---
id: 1211
title: "PUBLISH / Capture du README : script réparé, reproductible, régénérée par publish.sh"
status: done
who: "Claude"
due_date: 
updated_at: 2026-11-22T15:04:10
classified_at: 2026-11-22T15:04:09
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: ops
section_title: "Ops & deployment"
---

# #1211 — PUBLISH / Capture du README : script réparé, reproductible, régénérée par publish.sh

**TL;DR** — `pdm run screenshots` plantait depuis l'ajout de la colonne `attachement` et la capture du README datait de la v0.1.84. Script réparé, capture rendue reproductible, et `publish.sh` la régénère désormais à chaque publish local.

## Demande

- « peux-tu mettre à jour les screenshot (pdm run screenshot) »
- « peux-tu ajouter la tâche dans le publish ? »

## Résolution

### Modifications

- `scripts/screenshots.py`
  - `task_create` reçoit `attachement=None` (le script levait `KeyError: 'attachement'`, personne ne le lançait).
  - Purge de la base de test alignée sur la fixture `clean_db` de `tests/conftest.py` (activities, classifications wiki, tokens, burndown, scopes).
  - `_renumber_tasks()` : les tâches de démo sont renumérotées 1..n. Les ids sont en AUTO_INCREMENT et l'utilisateur de test n'a pas de droit DDL pour remettre le compteur à zéro ; sans ça chaque run changeait les `#id` affichés et réécrivait le PNG.
  - Serveur lancé par `werkzeug.serving.make_server` au lieu de `app.run` : plus de bannière `WARNING: This is a development server`, que `publish.sh` aurait remontée en ⚠ (#1130).
- `publish.sh`
  - Nouvelle étape `README Screenshots (playwright)` après les tests E2E, hors `--ci` (mêmes besoins : base de test + navigateurs). Compteurs : 25 → 26 en `--quality`, 39 → 40 en publish.
  - Reprise de la capture juste après le bump et la synchro de version (même étape que le bump, hors `--ci`) : l'en-tête du board affiche la version, le commit de release embarque donc un PNG à la bonne version.
- `doc/images/kanban.png` : régénérée (v0.5.7, ids `#1` à `#8`).
- `README.md` : mention que `publish.sh` régénère la capture.

### Comportements obtenus

- Trois runs consécutifs de `pdm run screenshots` produisent le même fichier (même sha1) : à version égale, le PNG ne change que si l'UI change.
- Si le script casse, le publish s'arrête à l'étape 25, avant tout push ou bump.
- En `--ci` (publish planifié du lundi sur GitHub) la capture n'est pas reprise : le PNG garde la version du dernier publish local.

### Limites

- Le PNG (~150 Ko) change à chaque release locale puisque la version y figure ; il s'ajoute à l'historique git. Alternative non retenue à ce stade : masquer le badge de version dans la capture.
- La reprise après bump n'a pas été exécutée (elle ne tourne que lors d'une vraie release) ; seule l'étape 25 l'a été.

### Garde-fous

- `sh publish.sh --quality` : 26/26 étapes ✓, aucune ligne ⚠, 825 tests unitaires, 52 e2e, gate métriques PASS.
- `sh -n publish.sh` : syntaxe ok.
---

[← retour à ops](index.md) · [voir log](../log/2026-11-22.md)
