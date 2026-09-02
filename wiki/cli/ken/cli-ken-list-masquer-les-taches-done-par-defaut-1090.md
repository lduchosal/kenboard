---
id: 1090
title: "CLI / ken list — masquer les tâches done par défaut"
status: done
who: "Claude"
due_date: 
updated_at: 2026-09-02T09:19:31
classified_at: 2026-09-02T09:04:11
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: cli/ken
section_title: "ken task CLI"
---

# #1090 — CLI / ken list — masquer les tâches done par défaut

Analyse du changement de comportement proposé : `ken list` masquerait les tâches `done` par défaut.

## Constat

`ken list` sans filtre imprime 293 lignes sur ce projet, **toutes `done`** (mesure 2026-09-02 : total 293, `Counter({'done': 293})`). Le bruit croît avec l'historique du board, donc la commande devient inutilisable pour sa fonction première — voir le travail ouvert.

## Cause

- `list_tasks` (`src/dashboard/ken/tasks.py:37-52`) : `GET /api/v1/tasks?project=<id>` puis filtrage `--status` / `--who` **côté client**. Sans flag, tout est imprimé — et tout est aussi transféré.
- La route `GET /api/v1/tasks` (`src/dashboard/routes/tasks.py:24-38`) ne connaît que le paramètre `project` ; `task_get_by_project` (`src/dashboard/queries/tasks.sql:1`) renvoie tous les statuts, ordonnés par position.
- Rien n'archive ni ne borne la colonne `done` → croissance monotone.

Les instructions agent ne sont pas en cause : `2113.ch/CLAUDE.md:179` et `kenboard/CLAUDE.md:147,166` passent déjà des filtres natifs explicites. Le défaut du CLI, lui, déverse l'historique complet.

## Changement proposé

`ken list` masque `done` par défaut ; `--all` (et `--status done`) le rétablit.

## Périmètre d'impact (analysé)

Autres consommateurs du même endpoint — ils ont **besoin** des tâches `done`, à ne pas toucher :

| Appelant | Ligne | Besoin |
|---|---|---|
| `ken show` | `tasks.py:118` | récupère toute la liste puis filtre par id |
| `ken polish` | `polish.py:80` | idem |
| `ken sync` | `sync.py:68` | écrit un fichier par tâche, `done` incluses |
| `ken init` | `cli.py:87` | appel de vérification d'accès (fallback board ancien), ne lit pas le contenu |

⇒ le filtre doit rester **local à la commande `list`**, jamais dans `_request` ni dans la route.

Non concernés : chaîne wiki (`wiki_sync`, `wiki_groom`, `wiki_lint` → endpoints `/api/v1/wiki/*` distincts) ; extension navigateur (`extension/options.js:82`, appelle l'API directement).

## Risques

- Changement de défaut d'un CLI publié sur PyPI. `ken list --json` est documenté (`KENBOARD.md:22`) comme entrée de parsing LLM : un consommateur qui comptait sur « tout » verra moins de lignes. Mitigation : `--all`, entrée CHANGELOG, mise à jour de `doc/ken-cli.md` (synopsis ligne 20) et de `KENBOARD.md`.
- Aucun impact sur les instructions agent (filtres déjà explicites).

## Tests

- `tests/unit/test_ken.py::TestCliList` : `test_columns_output` (todo/doing) et `test_status_filter` restent verts. `test_json_output` fournit une tâche **sans clé `status`** → elle survit à un filtre `t.get("status") != "done"` ; cas limite à conserver tel quel.
- À ajouter : `done` masqué par défaut, `--all` le montre, `--status done` le montre.

## Piste adjacente (hors périmètre, à arbitrer)

`ken show <id>` et `ken polish <id>` téléchargent les 293 tâches pour n'en garder qu'une, alors que `GET /api/v1/tasks/<id>` existe (`routes/tasks.py:41`). Le vrai correctif de volume est double : filtre serveur (`?status=`) sur la liste + usage de la route by-id dans `show`/`polish`.
---

## Résolution

### Modifications

- `src/dashboard/ken/tasks.py` — `ken list` gagne `--all` ; `done` est filtré par défaut, `--all` + `--status` lève une `UsageError`, le compte des masquées part sur stderr. `--who` est appliqué **avant** le filtre de statut pour que le compte décrive la vue demandée.
- `tests/unit/test_ken.py` — nouvelle classe `TestCliListDoneDefault` (7 cas).
- `doc/ken-cli.md` — synopsis + exemples de la section « Surface CLI ».
- `src/dashboard/agent_guide.md` — note dans « Filters and output » (c'est le texte servi par `ken help` aux agents).
- `KENBOARD.md` — bloc « Opérations courantes » (fichier gitignoré, hors commit).

### Comportements obtenus

Smoke-test réel contre le board :

```
$ ken list
(293 done hidden — ken list --all)
ID    STATUS  WHO     WHEN  TITLE
1090  doing   Claude  --    CLI / ken list — masquer les tâches done par défaut

$ ken list --all --json | wc -l        # 294 tâches, historique complet
$ ken list --json 2>/dev/null          # stdout parseable, hint sur stderr
$ ken list --all --status todo         # exit 2, "mutually exclusive"
```

Choix d'implémentation retenus :

- Le filtre **exclut `done`** (`!= "done"`) au lieu de sélectionner les statuts ouverts : une tâche au statut absent ou inconnu reste visible, et un cinquième statut ajouté un jour à `VALID_STATUSES` apparaîtra par défaut au lieu de disparaître en silence.
- Le compteur va sur **stderr** — convention déjà en place dans le fichier (`_save_attachement`) — donc `ken list --json | jq` reste valide. C'est aussi la réponse au risque propre à un défaut masquant : une tâche qui « disparaît » sans explication.
- `--all` + `--status` → `UsageError` plutôt qu'une règle de précédence à mémoriser.
- Filtre **client uniquement** : le `?status=` serveur et la route by-id pour `show`/`polish` restent hors périmètre (cf. § Piste adjacente).

### Garde-fous

| Gate | Résultat |
|---|---|
| `pdm run lint` (ruff) | PASS — TRY003/EM101 corrigés en alignant sur la convention `msg = ...` du repo |
| `pdm run typecheck` (mypy strict) | PASS, 65 fichiers |
| `pdm run check` (composite + metrics-gate) | PASS palier 5 ; DCO050/DCO053 corrigés (section `Raises:`, sans préfixe `click.`, comme `onboard_url.py`) |
| `pdm run test-unit` | 651 passed |
| `pdm run test-cov` | 711 passed, couverture totale 95.29 % (seuil 75), `ken/tasks.py` à 95 % — les 5 lignes non couvertes sont dans `_save_attachement`, antérieures |

**2 échecs pré-existants** : `tests/unit/test_auth_user.py::TestLoginRateLimit::{test_burst_blocked_after_5, test_429_response_includes_retry_after}`. Prouvés indépendants du changement — même `pdm run test-cov` sur l'arbre stashé donne les deux mêmes échecs (704 passed baseline vs 711 avec les 7 nouveaux tests). Ils ne tombent qu'en suite complète, pas en `test-unit` seul : dépendance d'ordre sur le compteur de rate-limit.

### Reste à faire (utilisateur)

Bump **minor** (0.3.0 → 0.4.0) via `sh publish.sh --minor` : changement de défaut d'un CLI publié sur PyPI, un patch mentirait. Non exécuté — publication sortante, décision utilisateur.
---

[← retour à cli/ken](index.md) · [voir log](../../log/2026-09-02.md)
