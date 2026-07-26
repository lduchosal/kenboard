---
id: 995
title: "QUALITY / sonar_gate — attendre CI/file CE au lieu du timeout aveugle"
status: done
who: "Claude"
due_date: 
classified_at: 2026-07-26T18:13:19
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #995 — QUALITY / sonar_gate — attendre CI/file CE au lieu du timeout aveugle

Incident publish 0.2.4 (26.07.2026) : le gate local a avorté après 900s alors que (a) la CI GitHub a mis ~14 min à être schedulée+exécutée, puis (b) la maintenance planifiée SonarQube Cloud (12:00-16:00 UTC) a gelé la file compute-engine ~70 min. Le rapport avait pourtant été soumis (tâche CE consultable via /api/ce/task pendant tout l'épisode) et le gate a fini PASSED. sonar_gate.py doit distinguer trois états au timeout de base : (1) aucune analyse soumise ET rien en cours → abort (comportement actuel, correct si la CI a cassé) ; (2) run GitHub Actions queued/in_progress pour le commit (sonde gh run list, best-effort si gh présent) → prolonger ; (3) tâche CE PENDING/IN_PROGRESS côté Sonar (/api/ce/component) → prolonger. Prolongation bornée par un cap dur --max-wait (défaut 3600s) ; grâce de quelques polls après drain de la file (l'analyse s'indexe avec un léger retard). Mettre à jour l'appel et le commentaire dans publish.sh. Garde-fous : script hors périmètre des gates (scripts/), mais code typé+docstrings google ; vérification fonctionnelle live sur le commit HEAD analysé.

---

## Résolution

### Modifications

- `scripts/sonar_gate.py` — `_wait_for_analysis` réécrit : double deadline (soft `--timeout` = attente aveugle, cap dur `--max-wait`, défaut 3600s). Au-delà du soft, l'attente ne continue que si `_ce_queue_busy()` (nouvelle sonde `/api/ce/component` : file ou tâche PENDING/IN_PROGRESS) ou `_ci_running()` (nouvelle sonde `gh run list --json headSha,status`, best-effort fail-open) répond vrai ; 2 polls de grâce après drain pour couvrir le délai d'indexation. Nouveau flag argparse `--max-wait`, message de timeout enrichi, docstring d'usage à jour. Nettoyage au passage (hors gate mais ruff clean) : imports triés, pathlib dans `_get_token`, chmod +x, noqa argumentés sur les catch fail-open délibérés (BLE001) et l'import optionnel certifi (PLC0415).
- `publish.sh` — appel du gate : `--timeout 900 --interval 20 --max-wait 3600` + commentaire retraçant l'incident.

### Comportements obtenus

- Échec CI (rien soumis, rien en cours) → abort à 900s, comme avant : le cas « fail fast » est préservé.
- Latence de scheduling GitHub (14 min observées) → couverte par la sonde gh tant que le run est queued/in_progress.
- File compute-engine Sonarcloud (maintenance 12:00-16:00 UTC, rapport en file ~70 min) → couverte par la sonde CE jusqu'au cap 3600s.
- Sondes fail-open : gh absent/non authentifié ou API CE en erreur = retour au comportement timeout simple, jamais d'attente infinie.

### Garde-fous

- `ruff check scripts/sonar_gate.py` : clean (D/PTH/BLE/PLC compris — scripts/ est hors gate, nettoyé quand même).
- Vérification fonctionnelle live : sondes à False hors activité ; gate complet contre HEAD `3a41178` → analyse trouvée, PASSED (avant et après refacto).
- Test grandeur nature : le publish 0.2.5 qui suit ce commit passera par le nouveau gate.
---

[← retour à quality](index.md) · [voir log](../log/2026-07-26.md)
