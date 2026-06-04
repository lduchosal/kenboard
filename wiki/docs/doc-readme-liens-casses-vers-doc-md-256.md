---
id: 256
title: "DOC / README / liens cassés vers doc/*.md"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:49
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: docs
section_title: "Documentation"
---

# #256 — DOC / README / liens cassés vers doc/*.md

Le `README.md` référence plusieurs fichiers sous `doc/` qui n'existent pas dans le dépôt :

- `doc/ken-cli.md` — promis comme "Full CLI" reference (section "References")
- `doc/api.md` — promis comme doc REST API (section "References")
- `doc/openapi.yaml` — promis comme spec OpenAPI (section "References")
- `doc/oidc-adfs.md` — promis comme guide ADFS (section "Enterprise")

Sur GitHub et PyPI, ces liens renvoient en 404, ce qui dégrade la première impression du projet.

---

## Résolution

### Diagnostic — origine de la perte

Investigation par `git log --all --diff-filter=D -- doc/` : les fichiers ont tous été supprimés dans **un seul commit, `1fdc315` ("chore: release version 0.1.66", 2026-04-19)**, qui efface ~2895 lignes sous `doc/` alors que son message ne mentionne qu'un bump de version. Probable suppression accidentelle (`git add -A` après un nettoyage local) jamais réconciliée avec le `README.md`.

Fichiers perdus dans ce commit (au-delà des 4 du README) :
- `doc/architecture.md` (référencé par `CLAUDE.md`)
- `doc/permissions.md`, `doc/burndown.md`, `doc/auth-user.md` (référencés par `INSTALL.md`)
- `doc/api-keys.md`, `doc/authentication.md` (orphelins mais utiles)
- `doc/uxui/empty/`, `doc/uxui/stitch_am_lioration_aide_web/` (assets de design)

### Modifications

- Restauration de tout l'arbre `doc/` à partir de `1fdc315^`, en excluant les `.DS_Store`. Commande utilisée :
  ```
  git checkout 1fdc315^ -- doc/api-keys.md doc/api.md doc/architecture.md \
      doc/auth-user.md doc/authentication.md doc/burndown.md doc/ken-cli.md \
      doc/oidc-adfs.md doc/openapi.yaml doc/permissions.md \
      doc/uxui/empty/{DESIGN.md,code.html,screen.png} \
      doc/uxui/stitch_am_lioration_aide_web/{DESIGN.md,code.html,screen.png}
  ```
- `doc/images/kanban.png` non restauré depuis `1fdc315^` : la version fraîchement régénérée par la tâche #255 (commit `e1fe0b5`) est conservée, plus à jour avec l'UI actuelle.
- Aucune modification du `README.md`, `CLAUDE.md` ou `INSTALL.md` : tous leurs liens `doc/*` résolvent désormais sans rien à toucher côté Markdown.

Restauration commitée et poussée dans `72b52b1` (le commit a malencontreusement embarqué des changements parallèles de couverture JS — l'audit trail de la restauration est un peu mélangé, mais le contenu est intact sur `origin/main`).

### Comportements obtenus

- `grep -nE '\\]\\(\\.?/?doc/' README.md CLAUDE.md INSTALL.md` → tous les liens pointent vers des fichiers existants.
- `find doc/ -type f` → 17 fichiers restaurés, 0 `.DS_Store`.
- Liens vérifiés : `doc/ken-cli.md`, `doc/api.md`, `doc/openapi.yaml`, `doc/oidc-adfs.md` (README), `doc/architecture.md` (CLAUDE.md), `doc/permissions.md`, `doc/burndown.md`, `doc/auth-user.md` (INSTALL.md).

### Garde-fous

- `git status` clean après push.
- Pas de quality gate (pdm run check / lint / etc.) : aucune ligne de code modifiée, uniquement des restaurations textuelles depuis l'historique git.

### À traiter dans une tâche de suivi (hors scope)

Les docs ont ~3 semaines (April 19 → May 6) et le code a beaucoup bougé entre-temps. Sondage rapide :

- `doc/api.md` affirme "Aucune authentification n'est requise pour le moment" — **faux** : l'API key middleware (`auth.py`) et Flask-Login (`auth_user.py`) sont en place.
- `doc/architecture.md` décrit le frontend comme "généré statiquement via Jinja2 ou servi dynamiquement par Flask" sans mentionner le bundling Vite (#251).
- `doc/openapi.yaml` ne couvre que l'endpoint `users` ; l'API a grossi depuis (categories, projects, tasks, keys).
- Probablement d'autres dérives mineures à passer en revue.

→ Créer une tâche dédiée "DOC / refresh des docs restaurées contre l'état courant du code" si souhaité. Hors scope ici car le titre de #256 était la résolution des liens cassés, pas la mise à jour de contenu.
---

[← retour à docs](index.md) · [voir log](../log/2026-05-24.md)
