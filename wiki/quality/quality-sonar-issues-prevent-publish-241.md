---
id: 241
title: "QUALITY / Sonar issues prevent publish"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:59
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #241 — QUALITY / Sonar issues prevent publish

Empecher la publication sur PyPI tant que le quality gate Sonarcloud ne passe pas.

---

## Resolution

### Modifications

- `scripts/sonar_gate.py` (nouveau) — Poll l'API Sonarcloud pour l'analyse du commit courant, verifie le quality gate, affiche les issues si KO. Utilise certifi pour SSL.
- `publish.sh` — Nouveau flux : push code → poll Sonarcloud → check gate → si OK bump+publish, si KO stop.
- `.env` — Ajout SONAR_TOKEN

### Flux publish.sh

1. Quality checks locaux (lint, tests, etc.)
2. `git push` — declenche l'analyse Sonarcloud
3. `scripts/sonar_gate.py` — attend l'analyse (timeout 5min, poll 15s)
4. Si gate OK → bump + build + publish PyPI + tag + push
5. Si gate KO → STOP, affiche les issues, pas de publication

### API Sonarcloud utilisees

- `/api/project_analyses/search` — trouver l'analyse du commit
- `/api/qualitygates/project_status` — verifier le gate
- `/api/issues/search` — lister les issues ouvertes (si gate KO)

### Garde-fous

- pytest unit : 368 passed
- Script teste avec succes (gate PASSED)
---

[← retour à quality](index.md) · [voir log](../log/2026-05-24.md)
