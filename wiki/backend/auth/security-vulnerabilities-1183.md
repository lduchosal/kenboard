---
id: 1183
title: "SECURITY / vulnerabilities"
status: done
who: "Claude"
due_date: 
updated_at: 2026-11-15T19:37:00
classified_at: 2026-11-15T18:45:53
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #1183 — SECURITY / vulnerabilities

**TL;DR** — Audit de sécurité du code kenboard (serveur, CLI `ken`, déploiement nginx) : 5 failles hautes et 6 moyennes, la plupart confirmées par PoC sur `dashboard_test`. Toutes sont corrigées dans l'arbre de travail via les tickets #1184 à #1195 (en review, non commités).

---

Analyse de sécurité du code kenboard : trouver les vulnérabilités (authn/authz, injection, XSS, CSRF, secrets, CLI, extension) puis discuter des findings avant tout correctif.

---

## Périmètre et méthode

- Lecture de `src/dashboard/` (auth, routes, modèles, requêtes SQL, templates, JS), du CLI `ken` (HTTP, config, init, wiki sync/build), survol de `extension/` et `vscode/`, et du déploiement (`ansible/roles/reverse`, `ansible/roles/kenboard`).
- PoC : 17 tests pytest sur `dashboard_test` uniquement, auth réellement active (`LOGIN_DISABLED=False`), via le client de test Flask. 16 passent ; le 17e est une variante de redirection (`next` contenant `\n`) qui lève une 500 au lieu de rediriger.
- Prod : trois GET en lecture seule (`/register` → 200, `/forgot-password` → 200, `/oidc/login` → 404). Aucun exploit tenté en prod.
- Statuts : **confirmé** = reproduit par PoC ; **déduit** = lecture de code, non exécuté.

## Synthèse

| # | Sévérité | Faille | Prérequis | Statut |
|---|---|---|---|---|
| H1 | Haute | Lien de reset de mot de passe détournable par `X-Forwarded-Host` | aucun compte ; la victime clique le lien du mail | confirmé |
| H2 | Haute | `/api/v1/wiki/all` et `/unclassified` renvoient toutes les tâches du board | n'importe quel compte connecté | confirmé |
| H3 | Haute | XSS stocké dans le wiki HTML, servi sur l'origine de Semaphore et Nagios | pouvoir écrire une description de tâche | rendu confirmé, chaîne Semaphore déduite |
| H4 | Haute | Une clé API écrit hors de son projet | une clé `write` sur un projet quelconque | confirmé |
| H5 | Haute | Contournement de `REGISTER_ALLOWED_DOMAIN` | aucun | confirmé sur Python 3.12.3, incertain en prod |
| M1 | Moyenne | Catégorie « Users » partagée entre tous les inscrits | compte auto-inscrit | confirmé |
| M2 | Moyenne | Mots de passe en clair dans le fichier de log | accès au log | confirmé |
| M3 | Moyenne | Sessions non révoquées au changement de mot de passe | cookie volé | confirmé |
| M4 | Moyenne | Open redirect après login | la victime suit un lien `/login?next=…` | confirmé |
| M5 | Moyenne | Durée de vie des clés API et tokens d'onboarding | clé d'un utilisateur supprimé, ou accès aux logs | confirmé / design |
| M6 | Moyenne | Pré-inscription avec le mot de passe de l'attaquant | la victime clique le lien de vérification | déduit |

Chaîne la plus courte : H5 puis H2 — un inconnu s'inscrit et lit tout le board.
Chaîne la plus grave : H4 puis H3 — une clé API d'un projet quelconque plante un script dans le wiki déployé sur l'origine de Semaphore.

## Failles hautes

### H1 — Reset de mot de passe détournable par `X-Forwarded-Host`

- **Où** : `src/dashboard/app.py:45` (`ProxyFix(x_for=1, x_proto=1, x_host=1)`), `src/dashboard/auth_reset.py:69` (`request.host_url`), même construction dans `src/dashboard/auth_register.py:118` (lien de vérification) et `src/dashboard/onboarding.py:47` (`derive_base_url`).
- **Déploiement** : `ansible/roles/reverse/files/nginx/sites/www.kenboard.2113.ch.conf:63-64` fixe `Host` et `X-Forwarded-For`, mais ni `X-Forwarded-Host` ni `X-Forwarded-Proto` : les en-têtes fournis par le client traversent nginx et ProxyFix leur fait confiance.
- **PoC** : `POST /forgot-password` avec `X-Forwarded-Host: evil.example` et l'e-mail de la victime → le mail légitime contient `https://evil.example/reset-password/<token>`.
- **Impact** : prise de compte, admin compris, dès que la victime clique. Limité par le rate limit (3/h par IP) et la validité du token (30 min).
- **Correctif proposé** : `x_host=0` (nginx fixe déjà `Host`) et `x_proto=0` ou en-tête posé par nginx ; idéalement une URL de base canonique en config pour tous les liens envoyés par mail. Mitigation immédiate côté ansible : `proxy_set_header X-Forwarded-Host $host;` et `proxy_set_header X-Forwarded-Proto https;` dans le vhost.

### H2 — Les endpoints wiki renvoient toutes les tâches

- **Où** : `src/dashboard/routes/wiki.py:34-95`. Le filtre `?project=` est optionnel ; sans lui, `wiki_get_all` et `wiki_get_unclassified_tasks` (`queries/wiki.sql:31,59`) renvoient toutes les lignes, sans filtrage par scope. La docstring annonce « every project the caller can see », ce que le code ne fait pas.
- **Pourquoi ça passe** : `/api/v1/wiki` n'est pas dans `ADMIN_ONLY_PREFIXES`, donc toute session cookie y accède. Les clés API, elles, sont bien bloquées (le middleware exige `?project=`).
- **PoC** : un utilisateur avec `read` sur la catégorie A reçoit 403 sur `/api/v1/tasks?project=<B>`, mais `GET /api/v1/wiki/all` lui renvoie titre, description, `who` et `project_id` des tâches classées de B, et `/unclassified` les titres des autres.
- **Impact** : lecture de tout le board par n'importe quel compte, y compris auto-inscrit. Divulgue aussi les UUID de projets, utiles pour H4.
- **Correctif proposé** : pour une session non admin, filtrer sur les projets des catégories où l'utilisateur a un scope (même logique que `proj_list_for_user`).

### H3 — XSS stocké dans le wiki HTML

- **Où** : `src/dashboard/ken/wiki_detail.py:14-18` — `markdown.markdown(md_text, extensions=[...])` sans assainissement, alors que la docstring dit « safe HTML ». Les descriptions de tâches sont injectées telles quelles par `ken wiki sync` (`ken/wiki_md.py:110-112`).
- **PoC** : `_render_markdown` laisse passer `<script>…</script>`, `<img src=x onerror=…>` et `[x](javascript:…)` sans modification.
- **Déploiement** : le wiki du board angel est servi sur `https://www.monitor.2113.ch/wiki/`, même origine que `/semaphore/` et les CGI Nagios, avec `Content-Security-Policy: default-src 'self' 'unsafe-inline'` (`ansible/roles/reverse/files/nginx/sites/www.monitor.2113.ch.conf:82`).
- **Impact (déduit)** : un script dans une page de tâche s'exécute avec la session Semaphore et l'auth basic Nagios de l'admin qui la consulte → lancement de playbooks, commandes Nagios. Non testé contre Semaphore.
- **Qui peut injecter** : tout principal pouvant écrire une description dans un projet exporté (utilisateur avec `write`, clé API, agent manipulé par injection de prompt), et via H4 une clé de n'importe quel autre projet. La publication reste manuelle (`angel publish`), ce qui laisse une fenêtre de relecture mais pas de garde-fou technique.
- **Correctif proposé** : assainir la sortie HTML dans `ken wiki build` (liste blanche de balises/attributs, schémas d'URL `http(s)`/`mailto`), et durcir la CSP de `/wiki/` côté nginx (pas de `'unsafe-inline'` pour les scripts).

### H4 — Une clé API écrit hors de son projet

- **Où** : `src/dashboard/auth_scopes.py:99,113` — `current_user_can*` renvoie toujours `True` pour un principal clé API, en supposant que le middleware a déjà vérifié le scope. Or `auth_resolve.py` ne résout que le projet *d'origine* de la requête.
- **Cas confirmés** avec une clé `write` sur le seul projet A :
  - `PATCH /api/v1/tasks/<id>` avec `{"project_id": "<B>"}` → la tâche passe dans B (`routes/tasks.py:233-238`). La création directe dans B est bien refusée (403).
  - `PATCH /api/v1/projects/<A>` avec `{"cat": "<autre catégorie>"}` → le projet change de catégorie (`routes/projects.py:121-126`).
  - `project_order` contenant des projets étrangers → leurs positions sont modifiées sans contrôle (`routes/projects.py:141-143`, idem `routes/categories.py:108-110`).
- **Impact** : écriture dans des projets hors périmètre. Combiné à H3 : classer une tâche piégée pendant qu'elle est dans A, puis la déplacer dans le projet exporté — la classification suit le `task_id`.
- **Correctif proposé** : pour une clé API, vérifier dans la route le scope sur le projet de destination (et la catégorie cible) au lieu du court-circuit ; restreindre `project_order` aux projets de la catégorie concernée.

### H5 — Contournement de `REGISTER_ALLOWED_DOMAIN`

- **Où** : `src/dashboard/auth_register.py:83` — seul contrôle : `email.endswith(f"@{domain}")`, aucune validation de format. `src/dashboard/email.py:94` passe la chaîne brute à `smtplib.sendmail`, qui en extrait le destinataire avec `email.utils.parseaddr`.
- **PoC** : sur Python 3.12.3, `a@evil.com (x@2113.ch`, `a@evil.com, x@2113.ch`, `<a@evil.com>x@2113.ch` passent le contrôle et donnent `RCPT TO:<a@evil.com>`. Le compte est ensuite créé avec cette chaîne comme nom et e-mail.
- **Incertitude** : sur Python 3.13.18, `parseaddr` strict refuse ces formes et la chaîne part telle quelle au MTA ; l'issue dépend alors du serveur SMTP. La version de Python en prod (py311 FreeBSD) est à vérifier.
- **Impact** : inscription ouverte à n'importe qui, donc accès à H2 et M1.
- **Correctif proposé** : valider strictement l'adresse (une seule adresse, partie locale et domaine conformes, domaine comparé après parsing) avant tout envoi.

## Failles moyennes

### M1 — Catégorie « Users » partagée
`src/dashboard/auth_register.py:187-204` : chaque inscrit reçoit `write` sur la catégorie commune « Users », qui contient les projets « personnels » de tous. PoC : mallory lit et supprime une tâche du projet d'alice. À trancher : comportement voulu ou bug ? Si bug, une catégorie par utilisateur ou un scope au niveau projet.

### M2 — Mots de passe en clair dans les logs
`src/dashboard/app.py:95-100` journalise le corps JSON de chaque requête `/api/` en DEBUG ; `src/dashboard/logging.py` met le handler fichier en DEBUG quel que soit le mode. Les corps de `POST /api/v1/users`, `/users/<id>/password` et `/users/<id>/reset-password` contiennent les mots de passe. Constaté dans `logs/dashboard.log` local ; en prod, `/var/log/kenboard/`. Les pièces jointes (jusqu'à 16 Mo) y passent aussi. Correctif : ne pas journaliser le corps, ou masquer les champs sensibles et tronquer.

### M3 — Sessions non révoquées au changement de mot de passe
`src/dashboard/routes/users.py:138` (self-service) et `:176` (reset admin) n'appellent pas `_rotate_session_nonce`, contrairement à `auth_reset.py:138` et à la docstring de `auth_user.py:64`. PoC : une seconde session reste valide après le changement. Correctif : tourner le nonce dans les deux routes.

### M4 — Open redirect après login
`src/dashboard/auth_login.py:156-164` : `_is_safe_url` accepte `/\t/evil.example` ; Werkzeug retire la tabulation et émet `Location: //evil.example`. Exploitable via `/login?next=/%09/evil.example`. Les variantes `/\evil` et `/ /evil` sont encodées et inoffensives. Correctif : rejeter tout caractère de contrôle et valider après `urlsplit` (pas de `netloc`, pas de schéma).

### M5 — Durée de vie des clés API et tokens d'onboarding
- `api_keys.user_id` est en `ON DELETE SET NULL` (`migrations/0011`) : supprimer un utilisateur laisse ses clés actives et sans propriétaire (confirmé).
- Les tokens d'onboarding (`routes/keys.py:120-147`) ont le scope `write`, aucune expiration, et restent valides indéfiniment après promotion en `onboarded`.
- Ils circulent en query string (`/onboard/…?token=`), donc dans les logs d'accès nginx envoyés à logstash/Elasticsearch, et chez tout service tiers qui récupère l'URL pour un agent.
- Correctif proposé : révoquer les clés à la suppression de l'utilisateur, donner une expiration aux tokens d'onboarding, et exclure la query string des logs pour `/onboard/`.

### M6 — Pré-inscription avec le mot de passe de l'attaquant
`src/dashboard/auth_register.py:94-128` : le mot de passe est choisi avant la preuve de possession de l'e-mail. Un attaquant soumet `victime@domaine` avec son propre mot de passe ; si la victime clique le lien reçu, le compte est créé avec un mot de passe connu de l'attaquant. Non testé. Correctif : faire choisir le mot de passe après la vérification.

## Durcissement

- `src/dashboard/app.py:55` : CSP avec `script-src 'unsafe-inline'`, donc aucun filet si un XSS passe ; `static/js/markdown.js:47` et `fullscreen.js:70` rendent le HTML brut si DOMPurify n'est pas chargé.
- Rate limit en mémoire par worker (4 workers en prod), pas de verrouillage par compte.
- Énumération d'utilisateurs : argon2 sauté quand le compte n'existe pas (`auth_login.py:147`), envoi SMTP synchrone sur `/forgot-password`, message « Un compte existe déjà » sur `/register`.
- `src/dashboard/auth.py:206` : comparaison de la clé admin non à temps constant.
- Le contrôle admin de `/api/v1/users` et `/api/v1/keys` repose uniquement sur le préfixe du middleware, sans vérification dans les routes. Les variantes de chemin testées (`//api/v1/users`, `/api/v1//users`, `/API/v1/users`, `/api/v1/users/.`) sont bloquées.
- `models/user.py` : `color` non validé (injection CSS, admin seulement) ; `who` des tâches sans longueur maximale.
- `src/dashboard/errors.py:74-94` : les 500 auto-filées en tâche embarquent la traceback complète.
- Pas de `MAX_CONTENT_LENGTH` applicatif (nginx limite à 20 Mo).
- Extension navigateur : token en `chrome.storage.local`, content script sur `<all_urls>` — survolé seulement.

## Ce qui est sain

- SQL entièrement paramétré (aiosql), aucune requête construite par concaténation.
- Rendu du board : DOMPurify 3.2.4 et `textContent` pour les champs utilisateur ; `jsesc` + autoescape Jinja tiennent dans les attributs `onclick`.
- CSRF : contrôle `Origin`/`Referer` sur les méthodes non sûres et cookies `SameSite=Lax`, `HttpOnly`, `Secure`.
- Tokens (clés API, reset, vérification) stockés hachés, 256 bits d'entropie ; mots de passe en argon2 avec politique de robustesse.
- pf limite le port 9090 aux reverse proxies : `X-Forwarded-For` n'est pas falsifiable en direct.

## Décisions ouvertes

1. **Mitigations immédiates côté ansible, sans release** : forcer `X-Forwarded-Host` / `X-Forwarded-Proto` dans le vhost nginx (ferme H1) et vider `REGISTER_ALLOWED_DOMAIN` en prod le temps de corriger H2 et H5.
2. **Modèle de menace** : board réservé à des personnes de confiance ou réellement multi-utilisateurs ? Fixe la priorité de H2 et M1 (catégorie « Users » voulue ou bug).
3. **Découpage** : une tâche ken par correctif, ordre proposé H1, H2, H4, H3, H5, puis les moyennes.

## Garde-fous

- PoC exécutés sur `dashboard_test` uniquement, nettoyée par la fixture `db` avant et après chaque test.
- Aucun fichier du dépôt modifié ; le fichier de PoC est hors dépôt (scratchpad de session).
- Aucune requête mutative ni tentative d'exploitation en prod.

---

## Résolution

Les trois décisions ouvertes ont été tranchées par la consigne « un ken par tâche, corriger tout » : un ticket par faille, plus un pour le durcissement.

### Correctifs

| Audit | Ticket | Objet | État |
|---|---|---|---|
| H1 | #1184 | Liens de mail : `X-Forwarded-Host` ignoré, `KENBOARD_BASE_URL` | review |
| H2 | #1185 | Listings wiki filtrés par scope | review |
| H3 | #1186 | Assainissement du HTML de `ken wiki build` | review |
| H4 | #1187 | Clés API confinées à leurs projets | review |
| H5 | #1188 | Validation stricte de l'adresse d'inscription | review |
| M1 | #1189 | Catégorie personnelle par inscrit | review |
| M2 | #1190 | Logs sans secrets | review |
| M3 | #1191 | Sessions révoquées au changement de mot de passe | review |
| M4 | #1192 | Redirection post-login sûre | review |
| M5 | #1193 | Clés révoquées avec leur user, échéance des liens d'onboarding | review |
| M6 | #1194 | Mot de passe choisi après la vérification d'e-mail | review |
| Durcissement | #1195 | Temps constant, gardes admin, fail-closed, validations, 413 | review |

Découvert en passant, sans rapport avec les correctifs : #1196 (deux tests de rate-limit dépendants de l'ordre d'exécution avec les e2e).

### Comportements obtenus

- Chacun des PoC de l'audit est devenu un test de non-régression (`tests/unit/test_sec_audit.py`, `test_registration.py`, `test_wiki.py`, `test_email.py`) : il échouait avant le correctif, il passe après.
- Les deux chaînes d'attaque décrites plus haut (H5 → H2, H4 → H3) sont coupées à chaque maillon.

### Reste à faire hors dépôt kenboard

- **Release et déploiement** : rien n'est commité, publié ni déployé ; la prod reste vulnérable tant que la version corrigée n'y tourne pas.
- **Ansible** : `KENBOARD_BASE_URL` dans le dotenv kenboard ; `X-Forwarded-Proto` posé par le vhost ; CSP plus stricte sur `/wiki/` de monitor ; exclusion de la query string de `/onboard/` des logs d'accès.
- **Données existantes** : purge des logs contenant des mots de passe (et rotation de ces mots de passe), comptes déjà inscrits encore dans la catégorie « Users » partagée, tokens d'onboarding jamais utilisés sans échéance.
- **Non traité** (détail dans #1195) : CSP `'unsafe-inline'`, stockage du rate limit, timing de `/forgot-password`, extension navigateur.

### Garde-fous

- `pdm run check` : exit 0, 817 tests hors e2e, gate métriques PASS.
- `pdm run test-cov` (e2e inclus) : 867 passés, 2 échecs pré-existants (#1196). Couverture 96,15 %, `pdm run metrics-gate` PASS.
---

[← retour à backend/auth](index.md) · [voir log](../../log/2026-11-15.md)
