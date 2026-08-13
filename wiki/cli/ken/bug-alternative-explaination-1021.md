---
id: 1021
title: "BUG - Alternative explaination"
status: done
who: "Claude"
due_date: 
updated_at: 2026-08-13T13:17:14
classified_at: 2026-08-13T08:58:05
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: cli/ken
section_title: "ken task CLI"
---

# #1021 — BUG - Alternative explaination

La cause : ken cherche .ken / ken.ini en remontant depuis le répertoire courant (config.py:139). Mes ken update étaient lancés avec cd <scratchpad> && ken update … pour être à côté du --desc-file ; là-bas il ne trouve aucune config et retombe sur DEFAULT_BASE_URL = http://localhost:9090, où quelque chose répond exactement 400 Method PATCH not implemented (try POST). Les commandes qui passaient (add, move, done, wiki *) étaient toutes lancées depuis D:\Arcantel\project3.

---

## Résolution

### Diagnostic — confirmé, et c'est bien la cause de #1013

Vérifié dans le code : `DEFAULT_BASE_URL = "http://localhost:9090"`
(`ken/config.py:29`), appliqué en `ken/config.py:214` **sans le moindre
avertissement** quand la recherche ascendante ne trouve ni `.ken` ni `ken.ini`.

Deux choses rendaient l'erreur indéchiffrable :

1. **Rien ne signale le fallback.** `_require_project` protège les commandes qui
   ont besoin d'un `project_id` (`list`, `add`) — elles échouent proprement sur
   « no project configured ». Celles qui adressent une tâche par id (`update`,
   `move`, `done`) n'ont aucun garde-fou : elles partent vers localhost:9090.
2. **Le message d'erreur cachait l'hôte.** `_request` n'affichait que le path :
   `HTTP 400 on PATCH /api/v1/tasks/1108`. Impossible de voir que la requête
   n'était jamais partie vers le board — d'où le diagnostic initial de #1013
   (WAF/ModSecurity côté reverse proxy), faux.

### Modifications

- **`src/dashboard/ken/config.py`** — `KenConfig` gagne `base_url_is_default`
  (vrai quand aucun `--base-url`, aucun `KEN_BASE_URL`, aucun fichier de config
  n'a fourni d'URL) et `search_root` (le répertoire d'où est partie la recherche
  ascendante). Le fallback devient une information, plus un silence.
- **`src/dashboard/ken/http.py`** — les erreurs nomment l'**URL complète** au lieu
  du seul path, et `_default_base_url_hint()` ajoute le diagnostic quand l'URL vient
  du défaut. `_request` est le **seul** point de sortie HTTP du CLI (aucun autre
  module de `ken/` ne touche `urlopen`) : les 8 modules appelants et les 3 familles
  d'endpoints (`/api/v1/tasks`, `/api/v1/projects`, `/api/v1/wiki`) en bénéficient
  donc sans exception.
- **`tests/unit/test_ken.py`** — `TestDefaultBaseUrlDiagnostic`, 4 tests qui
  **rejouent le scénario** : `ken update 1108 --desc-file …` depuis un répertoire
  sans config, urlopen mocké renvoyant exactement
  `400 Method PATCH not implemented (try POST)`.

### Comportements obtenus

Avant :

```
Error: HTTP 400 on PATCH /api/v1/tasks/1108: Method PATCH not implemented (try POST)
```

Après :

```
Error: cannot reach http://localhost:9090/api/v1/tasks/1108: [Errno 61] Connection refused
Hint: no .ken / ken.ini was found above /tmp/scratchpad, so ken used its built-in
      default base_url (http://localhost:9090) — this request never reached your board.
      Run ken from the project directory (--desc-file accepts an absolute path), or
      pass --base-url / set KEN_BASE_URL.
```

Idem sur le cas HTTP : `HTTP 400 on PATCH http://localhost:9090/api/v1/tasks/1108: …`
suivi du même Hint. Une 400 venant d'un board correctement configuré reste un
message nu, sans bruit (test dédié).

### Garde-fous

- Les 4 tests couvrent : le cas HTTP 400 (le bug d'origine, avec vérification que
  l'URL appelée est bien `http://localhost:9090/...`), le cas `Connection refused`
  (la forme la plus courante), le non-déclenchement quand `KEN_BASE_URL` est défini,
  et un endpoint **hors tasks** (`ken init` → `/api/v1/projects`) qui prouve que le
  diagnostic n'est pas spécifique aux tâches.
- `pytest tests/unit tests/integration` → **630 passed, 1 failed**. L'échec est
  `tests/integration/test_auth_oidc.py::test_oidc_login_redirects_to_idp`,
  **pré-existant** : reproduit à l'identique sur un worktree propre en HEAD sans
  aucune de ces modifications (il passe en isolation, c'est un couplage d'ordre
  entre fichiers de tests, hors périmètre ici).
- ruff, flake8 (DCO), mypy strict, interrogate 100 %, vulture, black → verts.

### Lien avec #1013

#1013 a été diagnostiqué comme un WAF ModSecurity refusant `PATCH` — c'était faux,
et cette tâche donne la vraie cause. Le middleware `X-HTTP-Method-Override` livré
sous #1013 **a été retiré** sur décision de Q (code, tests, config et docs), avec le
replay correspondant côté `ken`. Il ne reste de cet épisode que ce qui est livré
ici.

### Commit

`15b0c26` — fix(ken): message coherent quand base_url tombe sur le defaut (ken #1021)
---

[← retour à cli/ken](index.md) · [voir log](../../log/2026-08-13.md)
