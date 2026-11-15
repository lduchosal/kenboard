---
id: 1190
title: "SEC / Logs : mots de passe en clair dans le fichier de log"
status: done
who: "Claude"
due_date: 
updated_at: 2026-11-15T19:37:08
classified_at: 2026-11-15T18:45:12
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/perf
section_title: "Performance & observability"
---

# #1190 — SEC / Logs : mots de passe en clair dans le fichier de log

**TL;DR** — Le corps de chaque requête API (mots de passe compris) et les valeurs rejetées par la validation étaient écrits dans le fichier de log → les corps sont masqués/tronqués et l'`input` pydantic n'est plus journalisé.

---

Issu de l'audit #1183 (M2). app.py journalise le corps JSON de chaque requête /api/ en DEBUG et le handler fichier est toujours en DEBUG : mots de passe (création user, changement, reset) et pièces jointes finissent dans le log.

---

## Résolution

### Modifications

- `src/dashboard/logging.py` — `redact()` : masque à toute profondeur les valeurs dont la clé nomme un secret (`password`, `token`, `secret`, `key`…), tronque les chaînes au-delà de 200 caractères.
- `src/dashboard/app.py` — `log_request` journalise `redact(body)`.
- `src/dashboard/errors.py` — `_safe_pydantic_errors()` retire `input` (valeur rejetée, ou corps entier pour un champ manquant).
- `tests/unit/test_sec_audit.py::TestLogRedaction` — 4 tests, dont deux de bout en bout sur le contenu réel du log.

### Comportements obtenus

- Création d'un user, changement de mot de passe, mot de passe trop faible : aucun mot de passe dans les enregistrements de log.
- Une description ou une pièce jointe volumineuse n'occupe plus qu'une ligne tronquée.

### Reste à faire hors dépôt

- Les logs existants (`/var/log/kenboard/` en prod, `logs/dashboard.log` en local) contiennent encore les anciens enregistrements : à purger, et les mots de passe qui y figurent sont à considérer comme exposés.

### Garde-fous

- `pdm run check` : exit 0 — isort, black, docformatter, mypy strict, flake8, interrogate 100 %, refurb, ruff, vulture, biome, tsc, vitest, build Vite, 817 tests hors e2e, gate métriques PASS.
- `pdm run test-cov` (e2e inclus) : 867 passés, 2 échecs **pré-existants** et sans rapport (`TestLoginRateLimit`, dépendance d'ordre avec les e2e, reproduits sur HEAD intact — ticket #1196). Couverture 96,15 %, `pdm run metrics-gate` PASS.
- Non commité : les modifications sont dans l'arbre de travail, en attente de revue.
---

[← retour à backend/perf](index.md) · [voir log](../../log/2026-11-15.md)
