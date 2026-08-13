---
id: 1013
title: "BUG - Method PATCH not implemented (try POST"
status: done
who: "Claude"
due_date: 
updated_at: 2026-08-13T13:17:15
classified_at: 2026-08-13T13:16:41
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: cli/ken
section_title: "ken task CLI"
---

# #1013 — BUG - Method PATCH not implemented (try POST

Bash(ken update 1108 --desc-file ken-1108-resolution.md 2>&1; echo "exit=$?")
  ⎿  Error: HTTP 400 on PATCH /api/v1/tasks/1108: Method PATCH not implemented (try POST)

---

## Résolution

### Diagnostic — CORRIGÉ par #1021

> **Ce diagnostic était faux.** La cause réelle est dans #1021 : `ken` cherche
> `.ken`/`ken.ini` en remontant depuis le cwd, et la commande fautive était lancée
> depuis un scratchpad (`cd <scratchpad> && ken update … --desc-file …`) pour être à
> côté du fichier. Sans config trouvée, `base_url` retombe silencieusement sur
> `DEFAULT_BASE_URL = http://localhost:9090` (`ken/config.py:29` et `:214`), où un
> service local sans rapport répond exactement `400 Method PATCH not implemented
> (try POST)`. La requête n'a jamais atteint le board. Ce qui a rendu la méprise
> possible : `_request` n'affichait que le path, jamais l'hôte. Corrigé sous #1021.
>
> Ce qui suit (piste WAF/ModSecurity) est conservé tel quel comme trace de l'analyse.

### Diagnostic initial (erroné)

**Le bug n'est pas dans kenboard.** La chaîne `not implemented (try POST)` n'existe
dans aucune révision du repo (`git log -S`), et kenboard répond toujours en JSON sur
`/api/v1/*` — le corps reçu était du texte brut. La réponse vient d'une couche en
amont de Flask.

Vérifié contre la prod 2113 (sondes non authentifiées : le verdict WAF tombe avant
l'auth, donc rien de mutatif) :

| requête | réponse |
|---|---|
| `PATCH /api/v1/tasks/<id>` corps `{}` | 401 JSON de kenboard |
| idem avec 96 KB de description | 401 JSON de kenboard |

Ni la méthode ni la taille ne posent problème quand aucun WAF n'est sur le chemin.
La commande fautive ne visait pas `www.kenboard.2113.ch` mais l'instance interne
**kenboard.arcantel.ch**, derrière un reverse proxy ModSecurity — c'est lui qui
refuse `PATCH` avec un `400` et un corps texte. Même famille que **#131**
(ModSecurity refusant `PATCH`/`DELETE` sur `/api/v1/users/*` → 403, invisible dans
les logs kenboard, visible seulement dans l'`error.log` du proxy).

Le correctif racine est côté infra arcantel (autoriser les verbes sur `/api/v1/`).
Mais `ken` est publié sur PyPI et tourne derrière des proxies arbitraires : la
parade conventionnelle — celle que le proxy suggère lui-même — est le tunneling du
verbe réel sur `POST`.

### Modifications

- **`src/dashboard/method_override.py`** (nouveau) — middleware WSGI réécrivant
  `REQUEST_METHOD` depuis `X-HTTP-Method-Override` sur un `POST`.
- **`src/dashboard/app.py`** — le middleware enveloppe `wsgi_app` en position la plus
  externe (le verbe doit être réécrit avant le routage et avant les hooks d'auth).
- **`src/dashboard/config.py`** + **`.env.example`** — `KENBOARD_METHOD_OVERRIDE`
  (défaut `true`) pour couper la fonction quand un proxy bloque un verbe volontairement.
- **`src/dashboard/ken/http.py`** — `_request` rejoue une écriture refusée en
  `POST` + header ; `_send` isole le round-trip, `_is_app_error` /
  `_should_retry_with_override` portent la décision. Toujours stdlib, zéro dépendance
  ajoutée.
- **`tests/unit/test_method_override.py`** (nouveau, 10 tests) — contrat du middleware
  en WSGI pur + 2 tests end-to-end Flask.
- **`tests/unit/test_ken.py`** — classe `TestMethodOverrideFallback` (5 tests).
- **`INSTALL.md`** — § « Exigences WAF / ModSecurity » (symptômes, curl de
  diagnostic, fix côté proxy) + ligne `KENBOARD_METHOD_OVERRIDE` dans la référence
  `.env` ; **`doc/ken-cli.md`** — § « Proxies hostiles aux verbes REST ».

### Comportements obtenus

- `POST` + `X-HTTP-Method-Override: PATCH|PUT|DELETE` atteint la route du verbe réel.
- `ken update/move/done/delete` traverse un proxy method-hostile sans intervention,
  et l'annonce sur stderr (« replayed as POST + X-HTTP-Method-Override »).
- Le replay ne part que si le verbe est une écriture, que le code est 400/405/501,
  et que le corps d'erreur **n'est pas du JSON** — une vraie 400 de validation
  kenboard ne déclenche donc jamais de seconde écriture.
- Si le replay échoue aussi, c'est l'erreur d'origine qui est rapportée.

### Garde-fous

- **Aucun privilège gagné** : `PATCH`/`PUT`/`DELETE` ont déjà le même scope `write`
  que `POST` dans `auth.py`, et l'override vers un verbe safe (`GET`/`HEAD`/`OPTIONS`)
  est refusé — sinon une clé `write` pourrait lire, et le contrôle CSRF
  Origin/Referer (qui ne couvre que les verbes unsafe) serait contourné. Test dédié.
- La réécriture a lieu en WSGI, donc résolution de scope et CSRF voient le verbe
  effectif, pas le verbe tunnelant.
- `POST /api/v1/tasks/<id>` n'existe pas comme route → sur un serveur qui ignore le
  header, le replay se prend un 405 et ne mute rien. Test dédié.

### Gates

Exécutées dans un **git worktree isolé** (HEAD + ces seules modifications) : le
working copy portait au même moment un refactor concurrent de `ken/wiki_build.py`
vers `wiki_layout.py`/`wiki_md.py` qui cassait la collecte de `test_ken.py`
(`ImportError: _format_footer`) — sans rapport avec cette tâche, et pas touché.

- `pytest tests/unit` → **632 passed**, `pytest tests/integration` → **10 passed**.
- ruff, flake8 (DCO), mypy strict, interrogate (100 %), vulture, refurb, black,
  isort, docformatter → tous verts sur les fichiers modifiés.
- Effet de bord relevé : les 2 tests Flask échouaient en suite complète (401) parce
  qu'un fichier de test antérieur laisse la bypass d'auth de la fixture `app`
  (session-scoped) dans l'autre état. Fixture `auth_bypassed` locale avec
  sauvegarde/restauration → tests indépendants de l'ordre.


---

## Post-mortem — correctif retiré

Le middleware `X-HTTP-Method-Override` livré ci-dessus **a été retiré** sur décision
de Q : il corrigeait un problème qui n'existait pas. Retiré de l'arbre :

- `src/dashboard/method_override.py` et `tests/unit/test_method_override.py` supprimés ;
- câblage dans `app.py`, `KENBOARD_METHOD_OVERRIDE` (`config.py`, `.env.example`),
  § « Exigences WAF / ModSecurity » d'`INSTALL.md` et § « Proxies hostiles aux verbes
  REST » de `doc/ken-cli.md` : revert ;
- replay côté `ken` (`ken/http.py`) et `TestMethodOverrideFallback` : supprimés.

Il ne reste **rien** de ce ticket dans le code. Le vrai correctif est #1021 (URL
complète dans les messages d'erreur + diagnostic du fallback `base_url`), qui est ce
qui aurait évité cette fausse piste dès la première minute.

### Commit

Aucun : le correctif de ce ticket a été retiré avant tout commit, rien n'a été
livré sous #1013. Le commit qui clôt réellement le symptôme est `15b0c26` (#1021).
---

[← retour à cli/ken](index.md) · [voir log](../../log/2026-08-13.md)
