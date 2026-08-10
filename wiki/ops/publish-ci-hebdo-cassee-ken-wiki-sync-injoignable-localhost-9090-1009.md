---
id: 1009
title: "publish / CI hebdo cassée : `ken wiki sync` injoignable (localhost:9090)"
status: done
who: "Claude"
due_date: 
updated_at: 2026-08-10T18:13:32
classified_at: 2026-08-10T18:13:33
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: ops
section_title: "Ops & deployment"
---

# #1009 — publish / CI hebdo cassée : `ken wiki sync` injoignable (localhost:9090)

## Symptôme

Le workflow GitHub Actions **Publish Package** (cron `0 9 * * 1`, tous les lundis) échoue **systématiquement** depuis mi-juin. Dernier run : [31377773735](https://github.com/lduchosal/kenboard/actions/runs/31377773735) (2026-08-10, 4m01s).

```
23/30 Wiki Sync (ken wiki sync)
→ Running: pdm run ken wiki sync
Error: cannot reach http://localhost:9090/api/v1/wiki/all: [Errno 111] Connection refused
✗ Wiki sync failed
##[error]Process completed with exit code 1.
```

Tous les gates qualité passent (625 tests OK, coverage 94.28 %, metrics-gate palier 5 PASS) — seul le wiki sync casse.

## Diagnostic

`publish.sh` ligne ~212 :

> ```
> # ... Needs the board API (.ken token), hence publish-only: --quality/CI never reach this point.
> ```

Ce commentaire est **faux**. Le garde qui existe est `if [ "$QUALITY_ONLY" = true ]; then exit 0; fi` — il ne filtre que `--quality`. Le workflow lance `sh publish.sh --ci --patch` (sans `--quality`), donc `CI_MODE=true` **atteint bien** l'étape 23/30. Le compteur d'étapes CI (STEPS=30) inclut d'ailleurs les deux étapes wiki.

En CI il n'y a ni serveur kenboard ni `.ken` (gitignored) : `ken wiki sync` tape `DEFAULT_BASE_URL = "http://localhost:9090"` (src/dashboard/ken/config.py:29) → connection refused → publish avortée avant le bump de version.

Introduit par le commit qui a ajouté les étapes wiki à publish.sh (f5b5a8c, 0.2.1, 2026-06-10).

## Impact

Aucune release automatique depuis 0.2.1 — 8 runs planifiés consécutifs en échec (22.06, 29.06, 06.07, 13.07, 20.07, 27.07, 03.08, 10.08). Les versions 0.2.2 → 0.2.6 ont toutes été publiées à la main depuis le laptop. La notification d'échec hebdomadaire est devenue du bruit.

## Pistes de correction

1. **Skipper wiki sync/build quand `CI_MODE=true`** (aligner le code sur le commentaire) et passer STEPS de 30 à 28. Le wiki étant de toute façon poussé depuis le laptop (`wiki/` committé), la CI n'a rien à en faire. — piste privilégiée.
2. Rendre les deux étapes non fatales (warn + continue) si l'API board est injoignable — garde la porte ouverte à un futur runner ayant accès au board.

Vérifier aussi qu'aucune autre étape publish-only ne suppose à tort que la CI n'y arrive jamais.

## Garde-fou

Après correctif : `workflow_dispatch` manuel du workflow Publish Package pour valider un cycle complet, plutôt que d'attendre le lundi suivant.

---

## Résolution

Corrigé dans `publish.sh` (commit `d42f04b`), livré en **0.2.7**.

### Modifications

- `publish.sh` — étape *Wiki Sync* enveloppée dans `if [ "$CI_MODE" = false ]`, sur le modèle du garde E2E déjà présent. Commentaire du bloc réécrit : il affirmait à tort que `--quality`/CI n'atteignaient jamais ce point, alors que seul `--quality` sortait plus haut (`exit 0` après le metrics gate).
- `publish.sh` — étape *Wiki Build* **conservée en CI** : `wiki_build.py` ne touche pas l'API (seul `wiki_sync.py` appelle `/api/v1/wiki/all` via `_request`), il rend le `wiki/` committé hors-ligne → render check gratuit sur le runner.
- `publish.sh` — compteurs `STEPS` recalculés depuis les `print_step` réels : 22 communs (clean → pytest + metrics gate), +1 E2E et +1 wiki sync hors CI, +12 publish-only. Soit 22/23 en `--quality` et 34/36 en publish. Les étapes zip extension + GitHub Release (#480/#501) n'avaient jamais été comptées — la bannière affichait « 34/30 ».

### Comportements obtenus

- `publish.sh --ci` ne dépend plus d'un board joignable : la publication planifiée du lundi peut aller au bout (bump → PyPI → tag → release).
- `publish.sh` (laptop) inchangé : sync + build wiki toujours exécutés avant le commit de release.
- Bannière de progression exacte : le run local de validation a affiché `1/36` … `36/36` sans dépassement.

### Garde-fous

- `sh -n publish.sh` : OK.
- `sh publish.sh --patch` complet sur le laptop : 36/36 vert (mypy, flake8, interrogate, refurb, ruff, vulture, biome, tsc, vitest, pytest, Playwright E2E, metrics-gate, gate Sonarcloud), **0.2.7 publiée sur PyPI**, tag `kenboard-0.2.7` poussé, release GitHub créée avec `kenboard-extension-0.2.7.zip` + `.xpi` signé.
- Premier essai avorté à l'étape 16/36 sur un `npm ci` ETIMEDOUT (aléa réseau, sans rapport avec le correctif) ; relancé après `npm ping` OK.
- Reste à valider côté runner : un `workflow_dispatch` manuel de *Publish Package* confirmera le cycle CI complet, sans attendre le cron du lundi.
---

[← retour à ops](index.md) · [voir log](../log/2026-08-10.md)
