---
id: 992
title: "QUALITY / ruff 0.16 — adopter les 413 règles par défaut et réparer le gate"
status: done
who: "Claude"
due_date: 
updated_at: 
classified_at: 2026-07-26T15:36:48
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #992 — QUALITY / ruff 0.16 — adopter les 413 règles par défaut et réparer le gate

## Contexte

ruff a été mis à jour 0.13 → **0.16.0** (sorti le 25.07.2026). C'est le premier changement du jeu de règles par défaut depuis la 0.1.0 : **59 → 413 règles par défaut** (B/bugbear, UP/pyupgrade, SIM, FURB, PYI, ASYNC, LOG, ISC, sous-ensembles PLR/PLW/PLE, 10 DTZ, BLE001…). Notre config `extend-select` étend les défauts → tout le nouveau jeu s'applique d'un coup.

État constaté sur le repo (analyse du 26.07.2026) :

- `pdm run lint` (ruff --fix) a déjà appliqué les fixes sûrs → 3 fichiers modifiés en attente dans le working tree (noqa E402/BLE001 retirés par RUF100, `"...".encode("utf-8")` → littéraux bytes via UP012). Les 612 tests unit passent.
- **19 violations restantes** : 11× ISC004, 3× PLR0917, 1× LOG014, 1× SIM102, 1× SIM113, 1× SIM117, 1× UP031.
- **Régression silencieuse** : les nouveaux défauts ont RETIRÉ la plupart des règles pycodestyle — seuls E722/E902 restent actifs. E401, E402, E711, E712, E731, E741 ne sont plus vérifiés par ruff.
- **Gate cassé par interaction ruff↔flake8** : RUF100 a retiré `E402` du noqa partagé de `src/dashboard/cli.py:227` (E402 plus vérifié par ruff), mais flake8 vérifie toujours E402 et lit le même commentaire → `pdm run flake8` est rouge. Le composite `pdm run check` échoue donc à flake8 PUIS à lint.
- Redondances : `DTZ`, `BLE` et `UP017` de notre extend-select sont désormais dans les défauts. Les autres entrées gardent leur valeur (82 règles au-delà des défauts : PTH +33, RUF +15, PLR +8, ARG +5, TRY +4, G +4, PERF +3, FBT +3, EM +3, SLF +1, PLC0415, C901, ANN401).
- PLR1702 toujours en preview — le commentaire d'attente dans pyproject reste valable.
- Nouveauté 0.16 : commentaires `ruff: ignore[CODE]` avec raison native + flag `--add-ignore`. MAIS flake8 ne comprend pas cette syntaxe → tant que flake8 est dans le gate, rester sur `# noqa`.

## Ce qu'il faut faire

### Palier A — réparer le gate (adopter les nouveaux défauts, principe ratchet #788)

1. **Ré-ajouter `"E4", "E7", "E9"` à `extend-select`** pour restaurer l'acquis pycodestyle retiré des défauts (sinon perte de couverture E402/E711/E712/E731/E741 et divergence avec flake8).
2. **Restaurer `# noqa: E402, F401` sur `cli.py:227`** (import tardif délibéré, cf. commentaire existant) — corrige à la fois flake8 et ruff-avec-E4.
3. **Corriger les 19 violations** :
   - ISC004 (11× — polish.py, wiki_log.py, onboarding.py, perf.py) : parenthéser ou fusionner les concaténations implicites dans les littéraux de liste. Le fix `--unsafe-fixes` de ruff pose des parenthèses mal indentées → passer black derrière, ou fusionner à la main.
   - PLR0917 (task_edit.py:108, :170 — commandes click) : noqa argumenté, convention existante du palier 4 pour les commandes click. pages.py:83 : évaluer un passage en keyword-only sinon noqa argumenté.
   - LOG014 (errors.py:224) : remplacer `exc_info=True` par `exc_info=original` — faux positif de ruff (handler d'erreur Flask, `sys.exc_info()` actif hors bloc except), mais le fix explicite est plus précis de toute façon.
   - UP031 (charts.py:148) : % formatting → f-string.
   - SIM102 (auth_api_key.py:51), SIM113 (tests/e2e), SIM117 (tests/unit) : petits refactors réels, à fixer plutôt qu'ignorer.
4. **Committer les fixes sûrs déjà appliqués** (cli.py, errors.py, test_auth_user.py) avec le reste.
5. **Remonter le plancher à `ruff>=0.16`** (sans borne supérieure) dans les dev deps : la config (purge DTZ/BLE du palier B, commentaires) suppose les défauts 0.16. Pas de pin `<0.17` — on veut continuer à recevoir les améliorations ruff ; un futur upgrade qui fait rougir le gate = nouvelle tâche qualité (principe ratchet), pas un accident à empêcher.

### Palier B — rationaliser la config

6. Purger `DTZ`, `BLE`, `UP017` d'extend-select (couverts par les défauts) en préservant les commentaires d'acquis (ken #785, paliers). Les per-file-ignores `tests/**` gardent DTZ/BLE (toujours nécessaires pour désactiver des règles désormais par défaut).
7. Mettre à jour le commentaire de tête de `[tool.ruff.lint]` : les défauts ne sont plus « E4, E7, E9, F » mais les 413 règles 0.16 — l'acquis B/SIM/FURB/PYI/ASYNC/ISC/LOG se verrouille désormais par les défauts.
8. Surveiller la sortie de preview de PLR1702 (inchangé).

### Palier C — évolution outillage (optionnel, tâche séparée si retenu)

- ruff couvre désormais par défaut une grosse part de refurb (17 FURB) et de flake8. Candidats de consolidation à moyen terme : `FURB` complet en remplacement de refurb, règles `D` (convention google supportée) en remplacement de flake8-docstrings — réduirait le composite `check`. À chiffrer séparément ; ne rien changer au gate actuel dans cette tâche.
- `ruff: ignore[reason]` : à reconsidérer si flake8 sort un jour du gate.

## Garde-fous

- `pdm run check` complet vert à la fin (flake8 + lint + tests + metrics-gate).
- Vérifier la couverture avec `pdm run test-cov` (le metrics-gate ne tourne qu'en CI).
- Aucun `select =` dur : on garde `extend-select` pour continuer à hériter des évolutions des défauts.

Références : [blog Astral 0.16](https://astral.sh/blog/ruff-v0.16.0), analyse détaillée dans la session Claude du 26.07.2026.

---

## Résolution

Paliers A + B implémentés, commit `fd5a3aa` (14 fichiers, +92/−54).

### Modifications

- `pyproject.toml` — extend-select : `E4`/`E7`/`E9` restaurés (retirés des défauts 0.16), `DTZ`/`BLE`/`UP017` purgés (couverts par les défauts) ; commentaire de tête réécrit ; plancher `ruff>=0.16` **sans borne supérieure** (principe ratchet) ; `pdm.lock` re-hashé (`pdm lock --update-reuse`, versions inchangées).
- `src/dashboard/cli.py` — `# noqa: E402, F401` restauré (identique à HEAD au final) → flake8 et ruff-avec-E4 alignés.
- `src/dashboard/errors.py` — LOG014 : `exc_info=original` au lieu de `True` (handler Flask hors bloc except) + commentaire ; suppression du noqa BLE001 devenu inutile (RUF100).
- `src/dashboard/auth_api_key.py` — SIM102 : ifs imbriqués fusionnés dans `_is_admin_only`.
- `src/dashboard/routes/charts.py` — UP031 : `%`-formatting → f-string.
- `src/dashboard/routes/pages.py` + `category_page.py` — PLR0917 : `_build_context` passe ses datasets optionnels en keyword-only (`*`), appelants mis à jour (`cat_snapshots=`).
- `src/dashboard/ken/task_edit.py` — PLR0917 : `add`/`update` tout keyword-only (click invoque en kwargs) — pas de noqa supplémentaire, le PLR0913 argumenté existant suffit.
- `src/dashboard/ken/polish.py`, `wiki_log.py`, `perf.py` — ISC004 : concaténations implicites parenthésées ; concat mono-ligne résiduelle de polish.py fusionnée.
- `src/dashboard/onboarding.py` — ISC004 via extraction en variable `step3` (sort la concat du littéral) : le fichier repasse à 298 lignes (le parenthésage naïf crevait le plafond absolu 300 du metrics-gate).
- `tests/unit/test_auth_user.py` — fixes sûrs 0.16 (UP012 : littéraux bytes).
- `tests/unit/test_security_invariants.py` — SIM117 : `with` parenthésé combiné.
- `tests/e2e/test_dashboard.py` — SIM113 : `enumerate(..., start=1)`.

### Comportements obtenus

- Les 413 règles par défaut de ruff 0.16 sont adoptées telles quelles (aucun `select =` dur, l'héritage des défauts futurs continue).
- L'acquis pycodestyle (E402/E711/E712/E731/E741…) est restauré via extend-select — plus de divergence ruff↔flake8 sur les noqa partagés.
- `ruff check src/ tests/` : **0 violation**. B/SIM/FURB/PYI/ASYNC/ISC/LOG désormais verrouillés par les défauts (ratchet gratuit).

### Garde-fous

- `pdm run check` complet : isort, docformatter, black, mypy (0 erreur/60 fichiers), flake8, interrogate (100 %), refurb, ruff, vulture, gates JS (biome, tsc, vitest, vite build) — tous verts.
- 622 tests passent (unit + integration) ; couverture **94.35 %** (min fichier 76.92) via `pdm run test-ci` ; **metrics-gate palier 5 : PASS** avec données de couverture complètes.
- Palier C (consolidation refurb/flake8 dans ruff, `ruff: ignore[reason]`) volontairement non traité — tâche séparée si retenu.
---

[← retour à quality](index.md) · [voir log](../log/2026-07-26.md)
