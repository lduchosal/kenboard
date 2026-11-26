---
id: 1242
title: "QUALITY / Scorecard des dépendances : état versionné + alerte opérateur au publish"
status: done
who: "Claude"
due_date: 
updated_at: 2026-11-26T15:28:27
classified_at: 2026-11-25T23:49:42
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #1242 — QUALITY / Scorecard des dépendances : état versionné + alerte opérateur au publish

**TL;DR** — Pas de suivi de la santé des projets amont → `scripts/dep_scorecard.py` (étape publish non bloquante) relève l'OpenSSF Scorecard + l'attestation PyPI des 48 paquets runtime dans un historique versionné `doc/dep-scorecard.csv` + scoreboard `doc/dep-scorecard.md`, compare au dernier snapshot committé et sort chaque divergence en ⚠ ; un commentaire dans `publish.sh` (et `CLAUDE.md`) impose à l'agent qui publie de la rapporter à l'opérateur.

Suite de #1238. Complément **non bloquant** au gate : suivre dans le temps la santé des projets amont des dépendances (OpenSSF Scorecard : maintenance active, code review, CI, releases signées, branch protection, dangerous workflows…). Un score sous un seuil n'est pas un défaut de kenboard — d'où un état versionné + une alerte à l'opérateur, pas un échec du build.

## À faire

- **Script** `scripts/dep_scorecard.py` (stdlib only, urllib — même famille que `quality_metrics.py`) :
  - liste des dépendances runtime + extras résolues (nom + version) ;
  - pour chacune, scorecard via l'API **deps.dev** v3 (version → projet source GitHub → scorecard) ; fallback CLI `scorecard` à évaluer si l'API ne couvre pas un paquet ;
  - écrit un **fichier d'état versionné** (ex. `doc/dep-scorecard.json` ou `.csv` à la `doc/quality-history.csv`) : un snapshot par run (date, kenboard version) × paquet (version, repo source, score global, date du scorecard, checks clés : `Maintained`, `Code-Review`, `Signed-Releases`, `Dangerous-Workflow`, `Vulnerabilities`, `Branch-Protection`) → évolution lisible dans le temps et dans `git log -p`.
  - compare au snapshot précédent et sort les **divergences**.
- **Étape `publish.sh`** non bloquante : met à jour le fichier (committé avec la release par l'étape « Adding All Files to Git »), résume en une ligne ; chaque divergence en ligne ⚠ explicite.
- **Commentaire dans `publish.sh`** adressé au modèle qui lance le publish : consulter le scoreboard (fichier d'état + lignes ⚠ de l'étape) et **avertir l'opérateur** en cas de divergence, dans son rapport final — jamais la taire ni la « corriger » en éditant le fichier.

## Définition de « divergence » (à affiner)

- Score global en baisse ≥ 1 point vs snapshot précédent.
- Un check critique qui tombe à 0 (`Maintained`, `Dangerous-Workflow`, `Code-Review`).
- Repo source qui change (signal de reprise / fork).
- Nouvelle dépendance runtime (première apparition) — avec son score, pour revue.
- Paquet sans scorecard (pas de repo GitHub lié).
- Scorecard périmé (date ancienne) — à signaler sans bruit excessif.

## Garde-fous

- Réseau indisponible / API en erreur : ⚠ visible, pas d'échec du build, pas d'écriture d'un snapshot vide ou partiel qui fausserait la prochaine comparaison.
- Requêtes vers deps.dev : uniquement des noms/versions de paquets publics, aucun identifiant du projet ou de l'opérateur.
- `CLAUDE.md` / `doc/code-quality.md` : décrire le fichier d'état et la consigne d'alerte.

## Résolution

### Modifications

- `scripts/dep_scorecard.py` (nouveau) —
  - fermeture runtime via `scripts/runtime_deps.py` (cf. #1241) ;
  - **deps.dev** : repo source + attestation (`relationProvenance = PYPI_PUBLISH_ATTESTATION`, Trusted Publishing) ;
  - **API OpenSSF** (`api.securityscorecards.dev`, hebdo) pour le scorecard ; la copie deps.dev, figée au 2026-08-24 (requests 8.2 vs 7.8 réel, aiosql Maintained 0 vs 10), ne sert que de repli (`scorecard_source`) ;
  - CSV : un snapshot complet (une ligne/paquet, 18 checks) à chaque changement d'état observé — la seule date de refresh du scorecard ne compte pas ;
  - comparaison contre le dernier snapshot **committé** (`git show HEAD:`), CSV de travail = historique committé + ≤ 1 snapshot en attente → les runs `--quality` répétés ne gonflent pas l'historique et la divergence est ré-annoncée jusqu'au commit de release ;
  - divergences (`warning:`) : nouvelle dépendance runtime, score −1 ou plus, `Maintained`/`Dangerous-Workflow`/`Code-Review` > 0 → 0, repo source changé, attestation perdue, scorecard disparu ; notes : paquet sorti de la fermeture ;
  - MD généré depuis le CSV seul (déterministe) : résumé, divergences du dernier snapshot vs le précédent, table triée par score (marque « ancien » au-delà de 90 j) ;
  - deps.dev/OpenSSF injoignable → `warning:`, fichiers inchangés, exit 0. Premier run = baseline sans divergence.
- `doc/dep-scorecard.csv` + `doc/dep-scorecard.md` — baseline : 48 paquets, médiane 6.0, 9 sous 5, 7 sans scorecard (38 OpenSSF, 3 repli deps.dev), 29 avec attestation PyPI.
- `publish.sh` — step « Dependency Scorecard (OpenSSF, non-blocking) » après guarddog, avec le commentaire adressé à l'agent qui publie (lire le scoreboard + le log, rapporter chaque ⚠ verbatim, ne jamais éditer les fichiers d'état pour faire taire) ; les fichiers d'état partent avec le commit de release (« Adding All Files to Git »).
- `pyproject.toml` — script PDM `dep-scorecard`.
- `CLAUDE.md` — consigne « après tout publish.sh, lire `doc/dep-scorecard.md` et rapporter chaque ⚠ ».
- `doc/code-quality.md` § *Chaîne d'approvisionnement des dépendances* ; `tests/unit/test_dep_gates.py` (partagé avec #1241).

### Comportements obtenus

- `Scorecard: 0 divergence(s), median 6.0, 48 packages — baseline snapshot … pending — see doc/dep-scorecard.md` en ~5 s (8 requêtes parallèles).
- Simulation hors ligne (historique committé factice : flask à 9.0, aiosql attesté, gunicorn absent, paquet retiré) : 3 ⚠ (score 9.0 → 7.1, attestation perdue, nouvelle dépendance gunicorn) + 1 note ; second run identique, toujours 2 snapshots dans le CSV.

### Garde-fous

- `sh publish.sh --quality` : **30/30 vert** (cf. #1241).
- scripts : `ruff check` clean, `mypy --strict` 0 ; tests : divergences (paramétrées par signal, petite baisse ignorée, bump de version seul ignoré), new/removed, `same_state`, aller-retour CSV, rendu du board — 19 passed.
- À faire par l'opérateur : committer `doc/dep-scorecard.{csv,md}` (baseline), sans quoi chaque run reste en « baseline pending ».
---

[← retour à quality](index.md) · [voir log](../log/2026-11-25.md)
