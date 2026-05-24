---
id: 129
title: "CLEAN / This is a developement server do not use in prod"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:37
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: cli/kenboard
section_title: "kenboard admin CLI"
---

# #129 — CLEAN / This is a developement server do not use in prod

Analyser ce warning quand on démarre kenboard en prod et proposer une résolution

---

## Résolution

### Diagnostic

Le warning provient du serveur **Werkzeug** (le serveur de dev intégré à Flask) qui imprime explicitement `WARNING: This is a development server. Do not use it in a production deployment.` chaque fois qu'il démarre. La commande `kenboard serve` appelait `app.run()` qui lance Werkzeug — c'est strictement un serveur de **dev** : mono-thread, mono-process, non hardené, prévu pour l'auto-reload. Servir du trafic prod avec lui crée des files d'attente, des timeouts, et n'a aucune garantie de résilience.

La résolution propre consiste à **séparer clairement** les deux usages :
- `kenboard serve` reste le serveur de dev (Werkzeug) mais **refuse de démarrer sans `--debug`**
- une nouvelle commande `kenboard prod` enrobe **gunicorn** comme serveur WSGI de production

### Modifications

- **`src/dashboard/cli.py`** :
  - `serve` : ajout d'un refus si `--debug` n'est pas passé. Le message d'erreur pointe vers `kenboard serve --debug` (pour le dev) ou `kenboard prod` (pour la prod), avec un renvoi vers `INSTALL.md` section 7.
  - **Nouvelle commande `prod`** : enrobe gunicorn via `gunicorn.app.wsgiapp.WSGIApplication`. Options `--bind` (défaut `0.0.0.0:8080`) et `--workers` (défaut 4). Late-import de gunicorn pour donner un message d'erreur explicite (`pip install "kenboard[prod]"`) quand l'extra n'est pas installé. Sous le capot, réécrit `sys.argv` comme si l'opérateur avait tapé `gunicorn --bind … --workers … dashboard.app:create_app()` puis appelle `WSGIApplication().run()`.

- **`pyproject.toml`** :
  - Nouveau bloc `[project.optional-dependencies] prod = ["gunicorn>=21.0"]`. Permet `pip install "kenboard[prod]"` sans bloater les users qui n'utilisent que le CLI `ken` ou `kenboard build`.
  - `gunicorn>=21.0` ajouté au groupe `dev` pour pouvoir tester la voie succès de `kenboard prod` end-to-end (mock de `WSGIApplication`, pas de vrai démarrage de serveur).

- **`tests/unit/test_cli.py`** : 6 nouveaux tests
  - `TestServeProdGuard` (3 tests) : couvre le refus de `serve` sans `--debug` (avec et sans flags annexes `--host` / `--port`)
  - `TestProdCommand` (3 tests) :
    - `test_missing_gunicorn_gives_clear_error` : simule l'absence du module en patchant `sys.modules` → vérifie exit 2 + message qui pointe vers `pip install "kenboard[prod]"`
    - `test_invokes_gunicorn_with_default_argv` : mock `WSGIApplication` → vérifie que `sys.argv` est réécrit avec les défauts `0.0.0.0:8080` / 4 workers
    - `test_passes_custom_bind_and_workers` : vérifie la propagation des flags CLI à `sys.argv`

- **`INSTALL.md` section 7** : refonte complète
  - Section dev : précise que `kenboard serve` refuse sans `--debug` et explique pourquoi
  - Section prod : remplace l'ancien `pip install gunicorn` + commande gunicorn longue par :
    ```sh
    pip install "kenboard[prod]"
    kenboard prod
    ```
  - Mention de la commande gunicorn brute comme fallback pour les options avancées (config file, hooks, logs structurés)

### Workflow opérateur après le fix

```sh
# install
pip install "kenboard[prod]"

# init DB + admin
kenboard migrate
kenboard set-password Q

# démarrage
kenboard prod                           # défauts: 0.0.0.0:8080, 4 workers
# ou avec overrides
kenboard prod --bind 127.0.0.1:9090 --workers 8
```

Plus aucune mention de gunicorn dans l'usage quotidien — c'est un détail d'implémentation.

### Garde-fous

- `pdm run check` (composite isort, format, docformatter, typecheck, flake8, interrogate, refurb, lint, vulture, test-quick) → ✅ vert
- 252 tests unitaires verts (+6 vs baseline)
- Aucune dépendance ajoutée au runtime de base — gunicorn est strictement opt-in via `[prod]`
- Le test `test_missing_gunicorn_gives_clear_error` garantit que les users qui font `pip install kenboard` sans l'extra reçoivent un message exploitable plutôt qu'un `ImportError` cryptique
- Aucun changement de schéma DB, pas de migration

### Hors scope

- **Waitress** comme alternative pure-Python à gunicorn : pas implémenté en v1, peut être ajouté via un autre extra `[prod-waitress]` si besoin un jour
- **Vendoring gunicorn** : volontairement écarté (extensions C, license mixte, cauchemar de maintenance)
- **Auto-tuning du nombre de workers** (`2*CPU+1`) : laissé manuel, défaut 4 acceptable pour kenboard sur web2 (4 cores)
- **Logs structurés gunicorn** : laissés à la conf gunicorn directe pour les opérateurs avancés (cf. fallback dans `INSTALL.md`)
- **Service rc.d FreeBSD** : pas dans le scope kenboard, c'est de l'ops système
---

[← retour à cli/kenboard](index.md) · [voir log](../../log.md)
