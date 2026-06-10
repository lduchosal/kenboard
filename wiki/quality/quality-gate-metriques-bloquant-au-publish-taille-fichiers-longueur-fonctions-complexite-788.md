---
id: 788
title: "QUALITY / Gate métriques bloquant au publish (taille fichiers, longueur fonctions, complexité)"
status: done
who: "Claude"
due_date: 
classified_at: 2026-06-10T08:31:53
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #788 — QUALITY / Gate métriques bloquant au publish (taille fichiers, longueur fonctions, complexité)

## Besoin

SonarCloud mesure mais ne bloque pas le publish → dérive de qualité. Il faut un check métrique **bloquant** dans publish.sh --quality : taille max des fichiers, longueur max des fonctions, complexité.

## Outils candidats

1. **ruff** (déjà installé, zéro dep) — C901 (complexité cyclomatique, `max-complexity`), PLR0915 (too-many-statements), PLR0912 (branches), PLR0913 (args). Ne couvre pas le comptage de lignes brut par fichier/fonction.
2. **pylint** — C0302 `max-module-lines` (fichier), R0915 (statements par fonction). Lourd à ajouter juste pour ça.
3. **flake8-functions** — CFQ001 longueur max de fonction en lignes, s'ajoute au flake8 déjà en place.
4. **lizard** — NLOC/CCN/args par fonction, thresholds CLI + exit code non-zéro.
5. **xenon** (sur radon) — gate de complexité bloquant.
6. **Ratchet maison (recommandé)** — étendre `scripts/quality_metrics.py` (ken #783) avec un mode `--gate` : échec si un critère régresse vs le dernier snapshot de `doc/quality-history.csv` (funcs_over_50, files_over_500, max_file_lines, c901_over_10, ruff_debt…).

## Pourquoi le ratchet d'abord

Des seuils absolus (fichier ≤ 150 lignes, fonction ≤ 50) échoueraient immédiatement sur la baseline actuelle (max_file_lines = 2266, funcs_over_50 = 25). Le ratchet bloque la **dérive** dès maintenant sans bloquer les releases, puis on resserre vers des seuils absolus au fil du nettoyage (plan dans doc/code-quality.md).

## Intégration

- `pdm run metrics-gate` (nouveau) appelé par publish.sh --quality et inclus dans `pdm run check`.
- En complément : activer C901 + PLR091x dans le gate ruff (c901_over_10 = 3 seulement, vite à zéro).
- Seuils absolus cibles documentés dans doc/code-quality.md et durcis progressivement.

---

## Résolution

### Modifications

- scripts/quality_metrics.py — métrique min_file_cov (pire couverture par fichier), seuils absolus GATE_MAX/GATE_MIN, ratchet best-ever RATCHET_DOWN/RATCHET_UP, mode --gate (exit 1), migration d'en-tête CSV dans record(), mesure de dette en --extend-select (les noqa des règles du gate ne gonflent plus RUF100), DTZ sorti de DEBT_SELECT (verrouillé côté ruff).
- pyproject.toml — script pdm metrics-gate, ajouté au composite check ; section [tool.ruff.lint] extend-select = DTZ, PLR0402, UP017 (verrous des acquis #784/#785) + per-file-ignores DTZ sur tests/**.
- publish.sh — étape « Quality Metrics Gate (ratchet) » après les tests, dans les chemins --quality, --ci et publish complet.
- tests/unit/test_quality_metrics.py — 10 tests unitaires de la logique pure du gate.
- doc/code-quality.md — section « Gate bloquant (ken #788) » : les 3 mécanismes, le référentiel de règles, la politique de resserrage, le pourquoi-pas-150-lignes.
- doc/quality-history.csv — colonne min_file_cov, suppression d'une ligne transitoire enregistrée en plein milieu du refactoring #786 (39/40 fichiers).

### Comportements obtenus

- pdm run metrics-gate : PASS sur l'état courant ; échec dès qu'un plafond absolu est dépassé (fichier > 1000 lignes, fonction > 130, min_file_cov < 25, …) ou qu'un compteur régresse au-delà de son meilleur niveau historique (files_over_500, funcs_over_50, c901_over_10, ruff_debt, test_cov −0,5 pt). Le ratchet se resserre seul à chaque metrics-record committé.
- Sans données coverage, les règles de couverture sont sautées avec avertissement (publish --ci les exécute sur données fraîches).
- ruff verrouille immédiatement DTZ/PLR0402/UP017 ; C901 et PLR091x suivront à zéro (#789, principe ratchet).

### Garde-fous

- pdm run test-ci : 559 passed (10 nouveaux), couverture 89,54 %.
- metrics-gate : PASS. mypy strict : 0. vulture : 0. ruff lint : clean. isort/black/docformatter : clean.
- flake8 : 1 E305 préexistante dans src/dashboard/ken/wiki.py — WIP de l'agent refactoring (#789) en parallèle, non causée par cette tâche (aucun fichier src/ touché ici).

---

## Addendum — régime par paliers (2026-06-10)

Décision utilisateur après livraison, affinée en deux temps : cibles finales exigeantes (dev 100 % agentique = dette payable en heures d'agent), atteintes **par paliers bloquants** documentés dans doc/code-quality.md § Gate bloquant.

- **5 paliers** : (1) max_file ≤ 900, max_func ≤ 130, c901 = 0, ruff_debt ≤ 240 → … → (5) max_file ≤ 300, max_func ≤ 50, ruff_debt = 0, test_cov ≥ 90, min_file_cov ≥ 75. Palier courant = GATE_PALIER dans scripts/quality_metrics.py.
- **Procédure de resserrage** : gate vert → metrics-record committé (le ratchet fige) → édition GATE_PALIER/GATE_MAX/GATE_MIN au palier suivant + activation extend-select des familles à zéro → carte ken « QUALITY / Palier N » avec la sortie rouge comme liste de travail. Un gate vert n'est jamais un état stable ; on ne détend jamais un seuil sans décision humaine tracée.
- **État** : palier 1 ROUGE — c901_over_10 = 3 et ruff_debt = 255 > 240, soit exactement le périmètre de ken #789 (en cours). Le publish est gelé jusqu'au vert du palier 1.
---

[← retour à quality](index.md) · [voir log](../log/2026-06-10.md)
