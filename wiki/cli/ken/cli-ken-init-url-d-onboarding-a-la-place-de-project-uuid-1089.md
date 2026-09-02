---
id: 1089
title: "CLI / ken init : URL d'onboarding à la place de PROJECT_UUID"
status: done
who: "Claude"
due_date: 
updated_at: 2026-09-01T17:44:26
classified_at: 2026-09-01T17:36:49
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: cli/ken
section_title: "ken task CLI"
---

# #1089 — CLI / ken init : URL d'onboarding à la place de PROJECT_UUID

## Problème — l'œuf et la poule

`ken init` sert à créer la config locale (`ken.ini` + `.ken`) d'un repo. Mais
pour découvrir le board, il commence par un `GET /api/v1/projects`… sur
`cfg.base_url`. Or tant qu'aucun `.ken` / `ken.ini` n'existe, la chaîne de
résolution retombe sur `DEFAULT_BASE_URL = "http://localhost:9090"`
(`src/dashboard/ken/config.py:29`).

Donc : **il faut déjà une config pour que `ken init` puisse écrire la
config**. Sur une machine neuve, `ken init <project-uuid>` part vers
localhost:9090 → connection refused (ou pire, un service tiers qui répond,
cf #1013 / #1021).

Aujourd'hui le contournement est de passer par l'env (`KEN_BASE_URL`,
`KEN_API_TOKEN`) ou des flags avant `init` — c'est exactement ce que le
runbook d'onboarding évite de demander à un humain.

## Ce qui existe déjà

La route publique `/onboard/cat/<cat_id>/project/<project_id>`
(`src/dashboard/onboarding.py:181`, #137) sert déjà un runbook en
`text/plain`, et le bouton *copy onboard link* de `category.html` génère
l'URL complète, **token inclus** :

```
https://www.kenboard.2113.ch/onboard/cat/<cat_uuid>/project/<project_uuid>?token=kb_…
```

Cette URL porte à elle seule les trois inconnues : `base_url` (scheme + host),
`project_id`, `api_token`.

## Décision — l'argument devient l'URL d'onboarding

**`ken init <onboarding-url>` remplace `ken init PROJECT_UUID`.** L'argument
positionnel n'est plus un UUID de projet mais l'URL complète copiée depuis le
board. C'est un **changement d'interface assumé** : la forme UUID (et la
sélection interactive quand aucun argument n'est passé) est retirée — elle ne
pouvait de toute façon fonctionner que sur un poste déjà configuré, c'est-à-dire
exactement le cas où `init` ne sert à rien.

```sh
ken init "https://www.kenboard.2113.ch/onboard/cat/<cat>/project/<proj>?token=kb_…"
```

Comportement attendu :

1. Parser l'URL et en dériver, **sans passer par la chaîne de résolution de
   config** : `base_url` (`scheme://netloc`, le path `/onboard/…` est retiré),
   `project_id` (segment `project/<uuid>`) et `api_token` (query `token`).
2. Valider l'URL : schéma `http(s)`, path de la forme
   `/onboard/cat/<uuid>/project/<uuid>` → sinon message d'erreur explicite qui
   rappelle où trouver le lien (bouton *copy onboard link* de la catégorie).
3. Faire un fetch de vérification avec ces valeurs (l'URL d'onboard elle-même,
   ou `GET /api/v1/projects` sur le `base_url` dérivé) pour valider le token et
   récupérer le nom du projet ; erreurs distinctes pour 401 (token invalide /
   expiré), 404 (projet inconnu) et injoignable.
4. Écrire `ken.ini` (`project_id`, `base_url`, `description`) et `.ken`
   (`api_token` seul, mode 0600) + entrée `.gitignore`, comme aujourd'hui via
   `_write_config_files` (`src/dashboard/ken/cli.py`).
5. Ne **jamais** écrire le token dans `ken.ini` (versionné) — il ne va que dans
   `.ken`.
6. `--force` : mêmes garde-fous d'écrasement qu'aujourd'hui (`ken.ini` et `.ken`
   existants refusés sans le flag).

## Conséquences dans le code

- `src/dashboard/ken/cli.py` : `init()` prend `onboarding_url` (requis) ;
  `_choose_project()` n'a plus d'appelant → à supprimer avec son mode
  interactif, sauf si on le garde pour un usage futur (sinon vulture le
  signalera).
- Le `cfg` du groupe (`ctx.obj["cfg"]`) ne doit plus piloter `init` : `init`
  construit son propre `KenConfig` depuis l'URL. Les flags globaux
  `--base-url` / `--token` restent utilisables comme surcharge explicite.
- `src/dashboard/onboarding.py` : le runbook doit proposer `ken init <url>` en
  étape 1 (aujourd'hui il décrit la mise en place manuelle du token).

## Décisions (points tranchés)

### URL sur stdin

Le token en clair dans un argument de shell atterrit dans l'historique. Donc
`ken init` lit aussi l'URL **sur stdin** :

```sh
ken init -                     # lit l'URL sur stdin
pbpaste | ken init -           # colle directement depuis le presse-papier
```

- `-` comme argument = lire une ligne sur stdin (`sys.stdin.read().strip()`),
  même convention que `--desc -` de `ken add` / `ken update`.
- Ligne vide ou stdin fermé → erreur explicite, pas de fichier écrit.
- L'argument inline reste supporté (c'est ce que le runbook affiche), mais la
  doc recommande la forme stdin dès que le lien porte un `?token=`.
- Forme canonique unique : seule l'URL `/onboard/cat/<uuid>/project/<uuid>` est
  acceptée ; une URL de board (`/cat/<id>`) ou un UUID nu produisent un message
  d'erreur qui montre où cliquer (*copy onboard link*).
- URL sans `?token=` : on écrit `ken.ini` seul et on avertit — comportement
  actuel quand aucun token n'est résolu (`_write_config_files`).

### Documenter `ken init` dans la page d'onboarding — en complément

La page `/onboard/cat/<cat>/project/<proj>` **ne mentionne pas `ken init`** :
son étape « ## 2. Configurer » (`onboarding_text_full`,
`src/dashboard/onboarding.py:256`) fait copier à la main un bloc
`cat_id= / project_id= / base_url= / api_token=` dans un fichier `.ken`. Idem
pour le 401 agent (`onboarding_text`) et sa version JSON (`onboarding_json`).

**Décision : l'étape 2 reste telle quelle.** Le bloc manuel n'est pas cassé —
`.ken` continue de porter *toutes* les clés et prime sur `ken.ini` dans la
résolution (`_pick_value`, `src/dashboard/ken/config.py`) ; c'est la forme
historique, toujours supportée, et elle sert de secours quand `ken init`
échoue (pas de réseau, proxy, version de ken trop ancienne).

On **complète** donc l'étape 2 avec `ken init` présenté comme le chemin
rapide, sans retirer le copier-coller :

```
## 2. Configurer

   ken init -        puis coller l'URL de cette page (token compris)

   Écrit ken.ini (versionné : project_id, base_url, description)
   et .ken (0600, ajouté au .gitignore : api_token).

   Ou à la main, si ken init n'est pas disponible : copier le bloc
   ci-dessous dans un fichier .ken
   [bloc actuel, inchangé]
```

Les trois rendus doivent rester cohérents : `onboarding_text_full` (page
publique), `onboarding_text` (401 texte) et `onboarding_json` (401 JSON — la
clé `ken_file` garde sa description du bloc manuel, et gagne une clé pour la
commande `ken init`).

### `ken.ini` complet — clés wiki incluses — et versionné

`_write_config_files` n'écrit aujourd'hui que trois clés (`project_id`,
`base_url`, `description`) alors que la résolution en connaît sept
(`_resolved_fields`, `src/dashboard/ken/config.py`). Résultat : les chemins du
pipeline wiki restent implicites, chacun les redécouvre ou les subit.

`ken init` doit écrire le `ken.ini` **complet**, valeurs par défaut comprises,
pour que le fichier documente lui-même la convention du repo :

```ini
[ken]
project_id = <uuid>
base_url = https://www.kenboard.2113.ch
description = <nom du projet>
sync_dir = doc/kenboard
architecture = ARCHITECTURE.md
wiki_dir = wiki
wiki_html_dir = wiki-html
```

- Les défauts viennent des constantes existantes (`DEFAULT_SYNC_DIR`,
  `DEFAULT_ARCHITECTURE`, `DEFAULT_WIKI_DIR`, `DEFAULT_WIKI_HTML_DIR`) — écrites
  en clair plutôt que sous-entendues.
- Un `ken init --force` sur un repo existant ne doit pas écraser une valeur
  déjà personnalisée : relire le `ken.ini` en place et ne remplacer que
  `project_id` / `base_url` / `description`, en conservant les clés wiki.

**`ken.ini` est versionné** — c'est le pendant partagé de `.ken` :

- seul `.ken` va dans `.gitignore` (`_add_to_gitignore`) ; `ken.ini` ne doit
  **jamais** y être ajouté, et ne doit contenir aucun token.
- garde-fou à ajouter : si `ken.ini` se trouve déjà ignoré par une règle du
  repo (un `ken*` ou un `*.ini` trop large — `git check-ignore -q ken.ini`),
  `init` doit le signaler, sinon la config partagée ne part jamais chez les
  coéquipiers. Le `.gitignore` de ce repo (`.ken`, `.ken*`) ne capture pas
  `ken.ini`, mais rien ne le garantit ailleurs.
- `init` affiche en fin de run le rappel « `ken.ini` est à committer, `.ken`
  jamais ».

À noter : ce repo n'a **pas** de `ken.ini` aujourd'hui (tout vit dans `.ken`) —
la nouvelle commande en produira un, à committer.

### `--help` explicite sur le fonctionnement

Le `--help` doit suffire à comprendre d'où vient la config, sans lire
`doc/ken-cli.md`. Aujourd'hui il ne dit rien :

- `ken --help` se résume à « Ken — task CLI for the kenboard board. » et liste
  quatre flags de surcharge, sans un mot sur la chaîne de résolution ni sur le
  fait qu'en l'absence de config **tout part vers `http://localhost:9090`** —
  le piège de #1013 / #1021, invisible depuis l'aide.
- `ken init --help` décrit `ken.ini` / `.ken` mais reste muet sur *comment* on
  amorce : son usage affiche encore `[PROJECT_UUID]`.

À corriger :

1. **Docstring du groupe** (`cli()`, `src/dashboard/ken/cli.py`) : ajouter la
   chaîne de résolution `flag > env > .ken > ken.ini > défaut`, le défaut
   `http://localhost:9090` nommé explicitement comme « aucune config trouvée »,
   et le pointeur « commencer par `ken init <url-onboarding>` ».
2. **`init --help`** : usage `ken init [OPTIONS] ONBOARDING_URL`, un exemple
   d'URL complète, la forme `ken init -` (stdin), et le tableau de ce qui est
   écrit où — `ken.ini` versionné vs `.ken` 0600 + `.gitignore`. Dire
   explicitement qu'`init` **n'a besoin d'aucune config préalable**, c'est
   toute la raison d'être de la commande.
3. **Résumé court** dans la liste des commandes (première ligne de la
   docstring) : « Bootstrap la config du repo depuis l'URL d'onboarding du
   board. » plutôt que l'actuel « Initialize ``ken.ini`` (and ``.ken`` if a
   token is set) in… » tronqué.
4. **Messages d'erreur** qui font office d'aide contextuelle :
   `src/dashboard/ken/http.py:121` dit encore ``Run `ken init <UUID>` or set
   KEN_PROJECT_ID`` → doit pointer l'URL d'onboarding ; idem
   `src/dashboard/ken/cli.py:94` (`re-run ken init --force`) et
   `src/dashboard/auth_session.py:99` (docstring mentionnant
   ``ken init <category-id>``, forme qui n'existe pas).
5. **`ken help`** (`src/dashboard/agent_guide.md`) ne mentionne `ken init` nulle
   part : la section config (l. 214, 225) parle du `.ken` gitignored et renvoie
   au runbook. Y mettre la commande d'amorçage.

## Tests attendus

- `tests/unit/test_ken.py` : parsing de l'URL (avec/sans token, trailing slash,
  port explicite, http vs https), refus d'une URL malformée / non-onboard,
  refus d'un UUID nu avec un message qui pointe vers la nouvelle forme.
- Mode 0600 de `.ken`, absence du token dans `ken.ini`, ajout de `.ken` (et
  de lui seul) au `.gitignore`.
- `ken.ini` écrit avec les sept clés ; `--force` préserve un `sync_dir` /
  `wiki_dir` personnalisé.
- Forme stdin : `ken init -` avec l'URL sur stdin, et stdin vide → erreur.
- Aide : `ken --help` et `ken init --help` mentionnent la chaîne de
  résolution, le défaut localhost et la forme URL/stdin.
- `tests/e2e/test_ken.py` : le parcours init complet contre le serveur de test.
- `tests/unit/` onboarding : la page et les deux 401 mentionnent `ken init`
  **en plus** du bloc manuel, qui reste présent inchangé.

## Docs

`doc/ken-cli.md` (§ init + chaîne de résolution), `CLAUDE.md` (§ `ken` CLI
workflow, qui documente encore `ken init <project-id>`) et le runbook
d'onboarding.

*(Le token de l'exemple fourni a été volontairement tronqué ici — ne pas
stocker de token réel dans une description de tâche.)*

---

## Résolution

`ken init` prend désormais l'URL d'onboarding (ou `-` pour la lire sur stdin),
se configure uniquement à partir d'elle, écrit un `ken.ini` complet, et la
documentation — page d'onboarding, `--help`, messages d'erreur, `ken help`,
`doc/ken-cli.md` — décrit ce chemin.

### Modifications

**CLI `ken`**

- `src/dashboard/ken/onboard_url.py` (nouveau) — parsing du lien :
  `parse_onboarding_url` (schéma http(s), path `…/onboard/cat/<id>/project/<id>`,
  préfixe de reverse-proxy conservé dans `base_url`, `?token=` optionnel) et
  `read_url_argument` (`-` → stdin).
- `src/dashboard/ken/cli.py` — `init` prend `ONBOARDING_URL` (l'ancienne forme
  `PROJECT_UUID` et le choix interactif `_choose_project` sont retirés) ;
  `_config_from_link` construit le `KenConfig` depuis l'URL seule (le `cfg`
  résolu du groupe est ignoré — c'est justement le fallback localhost) ;
  `_verify_project` valide et récupère le nom. Docstrings du groupe et de
  `init` réécrites (chaîne de résolution, défaut localhost, forme stdin,
  fichiers écrits).
- `src/dashboard/ken/init_files.py` (nouveau, extrait de `cli.py` + `config.py`) —
  `ken.ini` avec ses **sept** clés (défauts wiki/sync en clair, valeurs
  personnalisées préservées par `--force`), `.ken` 0600 + `.gitignore`, refus
  d'écrasement, et `_gitignore_rule_hiding_ini` qui avertit si une règle
  (`ken*`, `*.ini`) masque le `ken.ini` versionné.
- `src/dashboard/ken/http.py` — `_request(..., hints={code: texte})` pour les
  messages 401/403 spécifiques à `init` ; `_try_request` pour un appel
  best-effort ; `_build_request` factorisé. Message `_require_project` mis à
  jour.

**Board**

- `src/dashboard/routes/projects.py` + `src/dashboard/auth_resolve.py` —
  `GET /api/v1/projects/<id>`, *project-scoped* : c'est la seule lecture qu'un
  token d'onboarding (limité à un projet) peut faire, le listing répondant
  `403 cannot resolve project for scope check`. Découvert en testant `ken init`
  contre le board de prod.
- `src/dashboard/onboarding.py` / `onboarding_runbook.py` (split) — l'étape 2
  du runbook affiche `ken init "<l'URL de la page>"` déjà remplie, puis
  `ken init -`, **au-dessus du bloc manuel laissé intact** ; le 401 texte et le
  401 JSON (`ken_init`) gagnent la même mention.

**Docs** — `doc/ken-cli.md` (surface, exemples, section `init`, tableau des
clés, onboarding), `doc/openapi.yaml`, `src/dashboard/agent_guide.md`
(`ken help`), `CLAUDE.md`, `INSTALL.md`, docstring de `auth_session._unauthorized`.

### Comportements obtenus

- `ken init "<url>"` et `pbpaste | ken init -` configurent un repo vierge sans
  aucune config préalable ; `.ken` en 0600 + `.gitignore`, `ken.ini` complet et
  committable, token jamais dans `ken.ini`.
- Erreurs qui guident : UUID nu ou URL de board → « takes the board's
  onboarding URL » + où cliquer ; 401 → token du lien invalide/expiré ; 403 →
  pas d'accès à ce projet ; `ken.ini` masqué par un `.gitignore` → warning.
- Board plus ancien sans `GET /api/v1/projects/<id>` : bascule sur
  `GET /api/v1/tasks?project=<id>` (même autorisation, `description` vide).
- `ken --help` expose la chaîne de résolution et le défaut localhost ;
  `ken init --help` montre l'URL, la forme stdin et les deux fichiers écrits.

### Garde-fous

- `pdm run lint` / `typecheck` / `flake8` / `interrogate` (100 %) / `vulture` /
  `refurb` : verts.
- `pytest tests/unit` : 644 passés. `tests/integration` : 10 passés.
  `tests/e2e` : 52 passés (dont `init` réel contre serveur live + DB).
- `scripts/quality_metrics.py --gate` : **PASS** (max_file_lines 284,
  max_func_lines 49, min_file_cov 83.0, test_cov 95.25 — au-dessus du record
  94.12). Le split `onboarding_runbook.py` / `init_files.py` a été fait pour
  rester sous le plafond de 300 lignes/fichier.
- Vérifié en vrai contre `www.kenboard.2113.ch` : URL sur stdin, token via
  `--token`, `ken.ini` + `.ken` écrits, et la bascule sur le probe `tasks`
  (le board déployé n'a pas encore la route by-id).
- Pré-existants, non liés : `test_auth_oidc::test_oidc_login_redirects_to_idp`
  et `TestLoginRateLimit` (×2) échouent selon l'ordre d'exécution — reproduits
  sur `git stash` d'un arbre propre.
---

[← retour à cli/ken](index.md) · [voir log](../../log/2026-09-01.md)
