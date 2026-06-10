# Code quality — critères, baseline et plan de nettoyage

> Tâche fondatrice : ken #783. Objectif : disposer de critères **mesurables et
> rejouables** pour voir la qualité du code Python évoluer dans le temps, et
> d'un plan de nettoyage priorisé.

## Mesurer

```sh
pdm run metrics            # snapshot des critères (table)
pdm run metrics-record     # idem + append dans doc/quality-history.csv
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

Le jeu `ruff_debt` (constante `DEBT_SELECT` du script) :
`PLC0415, PLR, DTZ, EM, TRY, PERF, PTH, FBT, ARG, BLE, SLF, G, ANN401, RUF`.
Exclus volontairement : les règles purement stylistiques en conflit avec black
(`COM812`, `D4xx`, `ISC001`) et les règles `S*` (bandit) dont les hits actuels
sont des faux positifs sur des noms de variables (`secret_key`, `token_line`)
ou du subprocess maîtrisé dans `cli.py` (audit 2026-06).

**Principe ratchet** : quand une famille de règles du jeu `ruff_debt` tombe à
zéro, on l'ajoute au `[tool.ruff.lint] select` du gate pour verrouiller
l'acquis, et on la retire de `DEBT_SELECT`.

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
