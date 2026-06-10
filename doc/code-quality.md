# Code quality — critères, baseline et plan de nettoyage

> Tâche fondatrice : ken #783. Objectif : disposer de critères **mesurables et
> rejouables** pour voir la qualité du code Python évoluer dans le temps, et
> d'un plan de nettoyage priorisé.

## Mesurer

```sh
pdm run metrics            # snapshot des critères (table)
pdm run metrics-record     # idem + append dans doc/quality-history.csv
pdm run metrics-gate       # gate bloquant (#788) : plafonds + ratchet, exit 1 si violation
```

Le script (`scripts/quality_metrics.py`) n'utilise que les outils déjà
installés dans la venv (ruff, mypy, vulture, refurb, interrogate, coverage) +
l'AST stdlib — zéro dépendance ajoutée. `test_cov` lit le dernier run de
`pdm run test-cov` / `test-ci` (lancer avant pour une valeur fraîche).

L'historique vit dans [`quality-history.csv`](quality-history.csv) (une ligne
par snapshot, committée). Convention : enregistrer un snapshot après chaque
chantier de nettoyage notable, au minimum à chaque release mineure.

SonarCloud (`lduchosal_kenboard`, gate vérifié par `publish.sh` via
`scripts/sonar_gate.py`) complète ces critères locaux pour la **duplication**
et l'historique long terme côté cloud.

## Critères suivis

| Critère | Définition | Baseline (2026-06-09, v0.1.132) | 2026-06-10 (v0.1.133) | Direction |
|---|---|---:|---:|---|
| `loc_src` | lignes totales `src/dashboard/**/*.py` | 8 101 | 8 317 | informatif |
| `max_file_lines` | plus gros fichier | 2 266 (ken.py) | 890 (auth_user.py) | ↓ |
| `files_over_500` | fichiers > 500 lignes | 3 | 2 | ↓ → 0 |
| `functions` | fonctions définies (AST) | 267 | 267 | informatif |
| `max_func_lines` | plus longue fonction | 126 (`groom`, ken.py) | 126 (`groom`, ken/wiki.py) | ↓ |
| `funcs_over_50` | fonctions > 50 lignes | 25 | 25 | ↓ |
| `c901_over_10` | fonctions de complexité cyclomatique > 10 (ruff C901) | 3 | 3 | ↓ → 0 |
| `ruff_debt` | findings du jeu de règles ruff *non encore imposées* (voir ci-dessous) | 267 | 255 | ↓ |
| `mypy_errors` | erreurs mypy strict | 0 | 0 | = 0 (gate) |
| `vulture` | code mort (confiance ≥ 80) | 0 | 0 | = 0 (gate) |
| `refurb` | findings refurb | 0 | 0 | = 0 (gate) |
| `docstring_cov` | couverture docstrings (interrogate) | 100 % | 100 % | ≥ 95 (gate) |
| `test_cov` | couverture de tests (hors e2e) | 89.29 % | 89.54 % | ↑, ≥ 75 (gate) |
| `min_file_cov` | pire couverture par fichier (#788 — attrape un module neuf sans tests) | — | 30.36 % (email.py) | ↑, ≥ 25 (gate) |

Le jeu `ruff_debt` (constante `DEBT_SELECT` du script) :
`PLC0415, PLR, EM, TRY, PTH, FBT, ARG, BLE, SLF, G, ANN401, RUF`
(`DTZ` puis `PERF` sortis en 2026-06, tombés à zéro et verrouillés dans le
gate ruff).
Exclus volontairement : les règles purement stylistiques en conflit avec black
(`COM812`, `D4xx`, `ISC001`) et les règles `S*` (bandit) dont les hits actuels
sont des faux positifs sur des noms de variables (`secret_key`, `token_line`)
ou du subprocess maîtrisé dans `cli.py` (audit 2026-06).

**Principe ratchet** : quand une famille de règles du jeu `ruff_debt` tombe à
zéro, on l'ajoute au `[tool.ruff.lint] select` du gate pour verrouiller
l'acquis, et on la retire de `DEBT_SELECT`.

## Gate bloquant (ken #788)

`pdm run metrics-gate` échoue (exit 1) dès qu'une règle est violée. Il est
exécuté par `pdm run check` **et** par `publish.sh` (chemins `--quality`,
`--ci` et publish complet), juste après les tests pour lire une couverture
fraîche. Trois mécanismes complémentaires :

### 1. Verrous ruff — par fonction, échec dès `pdm run lint`

Chaque famille tombée à zéro est activée dans `[tool.ruff.lint]
extend-select` (pyproject) : `DTZ` (acquis #785), `PLR0402` (acquis #784),
`UP017`. Les datetimes naïfs restent tolérés dans `tests/**`
(per-file-ignores). Prochaines activations, dès que leur compteur atteint
zéro : `C901 ≤ 10` (#789), `PLR0913` args ≤ 5, `PLR0912` branches ≤ 12,
`PLR0911` returns ≤ 6, `PLR0915` statements ≤ 50 (6 violations restantes,
portées par les mêmes fonctions que #789), `PLR1702` imbrication ≤ 5 (dès
sa sortie de preview ruff).

### 2. Cibles par paliers (`GATE_MAX`/`GATE_MIN` du script)

**Régime décidé le 2026-06-10** : le développement étant 100 % agentique, la
dette se paie en heures d'agent — les cibles finales sont donc exigeantes et
**chaque palier intermédiaire est bloquant** dès son activation. Le palier
courant est `GATE_PALIER` dans `scripts/quality_metrics.py`.

| Palier | `max_file` | `max_func` | `c901` | `ruff_debt` | `test_cov` | `min_file_cov` | Chantier principal |
|---|---:|---:|---:|---:|---:|---:|---|
| 1 — ✓ fait 2026-06-10 | ≤ 900 | ≤ 130 | = 0 | ≤ 240 | ≥ 75 | ≥ 25 | ken #789 : C901 = 0, dette 238 — `C901`/`PERF`/`PLR0911/0912/0915` verrouillés dans ruff |
| **2 — actif** | ≤ 700 | ≤ 100 | = 0 | ≤ 150 | ≥ 85 | ≥ 40 | ken #798 : découpe `auth_user.py` (888) et `routes/pages.py` (701) ; fonctions > 100 (1) ; hygiène EM/TRY/PTH/G/FBT ; tests `email.py` (min_file_cov ≥ 40) |
| 3 | ≤ 500 | ≤ 80 | = 0 | ≤ 60 | ≥ 88 | ≥ 60 | découpe `routes/pages.py` (702) ; fonctions > 80 (5) ; tri PLC0415 (noqa argumentés ou remontés) ; tests `cli.py` |
| 4 | ≤ 400 | ≤ 60 | = 0 | ≤ 20 | ≥ 90 | ≥ 70 | fonctions > 60 (~14) ; gros du stock ANN401 |
| 5 — cible | ≤ 300 | ≤ 50 | = 0 | = 0 | ≥ 90 | ≥ 75 | dernières fonctions > 50 ; ANN401 = 0 |

(`mypy_errors`, `vulture`, `refurb` = 0 et `docstring_cov` ≥ 95 sont
bloquants à tous les paliers.)

### Procédure d'évolution des paliers

1. **Déclencheur** : `pdm run metrics-gate` passe au vert sur le palier
   courant. Un gate vert n'est **jamais** un état stable — c'est le signal
   de resserrage.
2. **Verrouiller** : `pdm run metrics-record` + commit du CSV (le ratchet
   fige le niveau atteint).
3. **Resserrer** : éditer `GATE_PALIER`/`GATE_MAX`/`GATE_MIN` dans
   `scripts/quality_metrics.py` selon le tableau ci-dessus ; activer dans
   `[tool.ruff.lint] extend-select` les familles tombées à zéro et les
   retirer de `DEBT_SELECT` (principe ratchet).
4. **Ouvrir le chantier** : créer la carte ken « QUALITY / Palier N » avec
   la sortie rouge de `metrics-gate` comme liste de travail, assignée aux
   agents.
5. **Palier 5 atteint** : le gate reste en place en mode verrou (cibles +
   ratchet) ; toute évolution ultérieure des seuils suit la même procédure.

Règle d'or : on ne **détend jamais** un seuil sans décision humaine
explicite, tracée dans une carte ken et dans l'historique du CSV.

### 3. Ratchet best-ever (vs `quality-history.csv`)

En complément des cibles, aucun compteur (`files_over_500`, `funcs_over_50`,
`c901_over_10`, `ruff_debt`) ne peut dépasser son **meilleur niveau
historique**, et `test_cov` ne peut pas tomber plus de 0,5 pt sous son
record : une fois la dette payée, le niveau atteint est verrouillé sans
aucun seuil à éditer. Une régression assumée exige une édition du CSV,
visible en revue. Sans données coverage (`pdm run test-quick` seul), les
règles de couverture sont sautées avec un avertissement — `publish.sh --ci`
les exécute toujours sur données fraîches.

**Pourquoi pas « fichier ≤ 150 lignes »** : la médiane du repo est à 152
lignes — ce seuil flaguerait la moitié des fichiers sans produire de signal.
La stratégie retenue : plafond large anti-monstre + stock décroissant
(ratchet) + cibles finales (fichier ≤ 500 puis 300, fonction ≤ 50,
complexité ≤ 10) atteintes par paliers et verrouillées une fois acquises.

## État des lieux (audit 2026-06-09)

Les gates existants sont **tous verts** : mypy strict 0 erreur, ruff (règles
par défaut) clean, interrogate 100 %, vulture 0, refurb 0, couverture 89 %.
La dette restante est donc structurelle, pas du laisser-aller :

- **`ken.py` = 28 % du code source** (2 266 lignes sur 8 101). Un seul module
  pour toute la CLI : config, client HTTP, rendu, commandes task, commandes
  wiki.
- **3 fonctions au-dessus du seuil de complexité 10** : `groom` (16,
  `ken.py:1208`, 126 lignes), `_resolve_project_id` (11, `auth.py:89`),
  `init_perf` (11, `perf.py:266`).
- **267 findings `ruff_debt`**, dominés par : `ANN401` ×111 (`Any` dans les
  signatures), `PLC0415` ×48 (imports locaux — en partie délibérés pour le
  démarrage rapide de la CLI), `TRY003`/`EM10x` ×34 (hygiène des messages
  d'exception), `PLR0402` ×12 (auto-fixable), `DTZ` ×6 (datetimes naïfs).
- **Couverture inégale** : `email.py` 30 %, `cli.py` 42 % — le reste ≥ 83 %.

### Mise à jour 2026-06-10 (v0.1.133, post #784–786)

Le refactoring #784 (quick wins ruff), #785 (DTZ) et #786 (découpe de
`ken.py` en package `dashboard/ken/`) a purgé les étapes 1, 2 et 4 du plan :
`max_file_lines` 2 266 → 890, `files_over_500` 3 → 2, `ruff_debt` 267 → 255,
`DTZ` et `PLR0402` à zéro. Reste inchangé :

- **`c901_over_10` = 3** — `groom` (16, `ken/wiki.py:164`, toujours 126
  lignes), `_resolve_project_id` (11, `auth.py:89`), `init_perf` (11,
  `perf.py:266`). Étape 3 du plan, non couverte par #784–786 → ken #789.
- **`funcs_over_50` = 25** — le découpage a déplacé les fonctions sans les
  raccourcir. Top : `groom` 126, `_build_taskers_daily_chart` 110
  (`routes/pages.py`), `category` 90 (`routes/pages.py`),
  `onboarding_text_full` 82, `verify_email` 81 (`auth_user.py`).
- **2 fichiers > 500 lignes** : `auth_user.py` (891), `routes/pages.py` (702).
- **`ruff_debt` 255**, dominé par `ANN401` ×111, `PLC0415` ×48, `FBT001` ×18,
  `TRY003` ×17, `RUF100` ×10 (noqa rendus obsolètes par le refactoring —
  auto-fixables), `EM10x` ×17.
- **Couverture** : `email.py` 30 % et `cli.py` 42 % restent les points
  faibles ; le nouveau `ken/cli.py` est à 74 %, le reste ≥ 83 %.

## Plan de nettoyage proposé (priorisé)

1. ~~**Quick wins auto-fixables**~~ — ✅ fait (ken #784, 2026-06-10).
   Nouveaux `RUF100` ×10 apparus depuis (noqa obsolètes post-refactoring),
   auto-fixables au prochain passage.
2. ~~**Datetimes naïfs (`DTZ005`/`DTZ011`)**~~ — ✅ fait (ken #785,
   2026-06-10). `DTZ` = 0.
3. **Casser la complexité des 3 fonctions C901** — extraire des helpers de
   `groom`, `_resolve_project_id`, `init_perf`. Cible : `c901_over_10 = 0`,
   puis ajouter `C901` au gate ruff (ratchet). → ken #789.
4. ~~**Découper `ken.py` en package**~~ — ✅ fait (ken #786, 2026-06-10).
   `max_file_lines` 2 266 → 890, entry point `dashboard.ken:cli` conservé.
5. **Couverture `email.py` (30 %) et `cli.py` (42 %)** — tests unitaires sur
   l'envoi SMTP (mock `aiosmtpd` déjà en dev-deps) et les commandes admin.
   Cible `test_cov` ≥ 92 %.
6. **Hygiène des exceptions (`TRY003`/`EM101`/`EM102`, ×34)** — messages
   extraits en variables/constantes, au fil de l'eau quand on touche un
   fichier.
7. **Trier les `PLC0415` (×48)** — légitimes dans `ken.py`/`cli.py` (lazy
   import pour le démarrage CLI) : poser des `# noqa: PLC0415` argumentés ;
   les autres (routes, app) : remonter en tête de module.
8. **`ANN401` (×111)** — typer plus finement les `Any` (souvent les retours
   JSON des routes / payloads ken). Long terme, au fil de l'eau.

Chaque chantier = une tâche ken dédiée, avec un `pdm run metrics-record`
avant/après pour matérialiser le delta dans `quality-history.csv`.

## Hors périmètre local

- **Duplication** : pas d'outil local installé (et on n'en ajoute pas) —
  suivie par SonarCloud.
- **JS** : la qualité frontend a son propre gate (Biome + tsc + Vitest) ;
  cette page ne couvre que le Python.
