---
id: 185
title: "CI / Python package: Some jobs were not successful"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:41
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #185 — CI / Python package: Some jobs were not successful

Je pense que l'on ne devrait pas executer les tests e2e dans les environnement Windows
Ou il conviendrait d'installer MySQL sur les vm windows afin de régler le problème:

https://github.com/lduchosal/kenboard/actions/runs/24382568729/job/71209114300

Analyse et dis moi ce que tu en penses

---

## Résolution

### Modifications

- **tests/conftest.py** — Rendu les fixtures autouse `setup_test_db` et `patch_db_connection` résilientes à l'absence de MySQL (catch OperationalError). Les fixtures `db` et `app` font `pytest.skip()` si MySQL est indisponible.
- **tests/unit/test_csrf.py → tests/integration/test_csrf.py** — Déplacé ce fichier car c'est un test d'intégration (utilise `db`, `queries`, `app`).
- **pyproject.toml** — `test-ci` n'ignore plus `tests/integration/` (MySQL est disponible dans le CI Linux).
- **tests/unit/test_cli.py** — Skip des tests gunicorn sur Windows (`gunicorn` est Unix-only).
- **tests/unit/test_ken.py** — Skip des tests de permissions Unix sur Windows, fix du chemin `doc/kenboard` avec `os.path.join()`.
- **tests/unit/test_logging.py** — Skip du test de rotation de log sur Windows (file locking).

### Comportements obtenus

- Windows CI : les vrais tests unitaires passent, les tests DB/Unix sont skippés proprement
- Linux CI : 269 tests passent (unit + integration), coverage 86%

### Garde-fous

- `pdm run test-unit` : 259 passed
- `pdm run test-integration` : 10 passed
- `pdm run test-ci` : 269 passed, coverage 86%
- `pdm run lint` + `typecheck` + `flake8` + `interrogate` : all passed
---

[← retour à quality](index.md) · [voir log](../log.md)
