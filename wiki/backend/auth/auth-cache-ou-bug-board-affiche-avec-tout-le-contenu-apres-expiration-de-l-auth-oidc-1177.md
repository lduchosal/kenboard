---
id: 1177
title: "AUTH / CACHE ou BUG — board affiché avec tout le contenu après expiration de l'auth OIDC"
status: done
who: "Claude"
due_date: 
updated_at: 2026-11-13T09:35:22
classified_at: 2026-11-13T08:59:56
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #1177 — AUTH / CACHE ou BUG — board affiché avec tout le contenu après expiration de l'auth OIDC

**TL;DR** — Après expiration de la session, le board restait affiché avec tout son contenu : c'est le **cache du navigateur**, pas une fuite serveur (le serveur répond 302/401 à tout cookie périmé, prouvé par test). Correctif : `Cache-Control: no-store` sur toutes les réponses dynamiques (pages + API), et message « Session expirée » clair sur un 401 côté UI.

## Constat

Quand on se connecte à kenboard avec l'authentification OIDC et que l'auth
expire, on arrive à avoir une page du kenboard avec tout le contenu. Quand on
clique sur une carte, on est redirigé vers la page d'authentification. On a
l'impression que le kenboard envoie les données même avec une authentification
expirée. Est-ce un problème de sécurité ou de cache ?

## Pré-analyse (lecture du code, non reproduit)

Hypothèse : **cache navigateur**, pas une fuite serveur.

- Toutes les pages à contenu sont derrière `@login_required`
  (`routes/pages.py` `/`, `/help`, `/about` ; `routes/category_page.py`
  `/cat/<id>.html` ; `routes/admin_pages.py`). Session invalide → 302 `/login`
  (`auth_session.py:_unauthorized`).
- `/api/v1/*` passe par le middleware `auth.py:_enforce` → 401 sans session ni
  bearer.
- Le user loader re-vérifie `session_nonce` en base à chaque requête : un
  cookie périmé ne charge aucun utilisateur.
- En revanche **aucune réponse HTML ne porte de `Cache-Control`**
  (`app.py:security_headers` pose CSP, HSTS, etc. mais rien sur le cache). Le
  navigateur peut donc réafficher une copie locale du board sans requête
  serveur : bfcache (retour arrière), restauration d'onglet/de session,
  onglet resté ouvert. Le premier clic qui déclenche une vraie navigation
  reçoit le 302 → `/login`, d'où le symptôme.
- Le rôle ansible `kenboard` ne configure ni `proxy_cache` ni `expires` : pas
  de cache partagé côté nginx.

Reste un point de durcissement (sévérité faible) : sur un poste partagé, le
contenu du board reste lisible après logout/expiration via retour arrière ou
restauration d'onglet.

## À faire

1. Reproduire et trancher : session expirée (ou `session_nonce` tourné en
   base), recharger `/` → vérifier dans l'onglet Réseau que le document vient
   de `disk cache`/`bfcache` et non d'un 200 serveur. Contre-épreuve :
   `curl -i` avec le cookie périmé doit rendre 302.
2. Si confirmé : poser `Cache-Control: no-store` sur les réponses HTML
   authentifiées et sur `/api/v1/*` (pas sur les statiques `/app.js`,
   `/style.css`), dans `security_headers`.
3. Test d'intégration : cookie de session au nonce périmé → 302 sur `/` et
   `/cat/<id>.html`, 401 sur `/api/v1/...` ; en-tête `no-store` présent sur
   les pages authentifiées.
4. Optionnel : dans `static/js/api.js`, sur 401 en session cookie, rediriger
   vers `/login?next=…` au lieu de la modale « Non authentifié ».

## Résolution

### Verdict

Cache, pas bug de contrôle d'accès. Côté serveur, un cookie au
`session_nonce` périmé reçoit 302 → `/login` sur les pages et 401 sur
`/api/v1/*` (test `test_stale_session_gets_no_data`). Le contenu vu à l'écran
était la copie locale du navigateur, réaffichée sans requête faute de
`Cache-Control`. Le volet navigateur n'a pas été rejoué dans un vrai
navigateur : il est déduit de l'absence d'en-tête, à confirmer en prod après
déploiement (onglet Réseau : le document `/` doit porter `no-store`).

### Modifications

- `src/dashboard/app.py` — `security_headers` pose
  `Cache-Control: no-store` par `setdefault` : toutes les réponses dynamiques
  (pages, API, `/login`, redirections) ; les statiques gardent la politique
  de `send_static_file` (`no-cache` + ETag).
- `src/dashboard/static/js/api.js` — un 401 affiche « Session expirée —
  Rechargez la page pour vous reconnecter » au lieu de « Non authentifié /
  unauthorized ». Pas de redirection automatique (point 4 de l'à-faire
  écarté) : elle ferait perdre une saisie en cours.
- `src/dashboard/static/js/api.test.js` — test 401 aligné.
- `src/dashboard/static/dist/app.js(.map)` — bundle régénéré.
- `tests/unit/test_logout_invalidates.py` — classe `TestNoStore` (5 tests).

### Comportements obtenus

- Page authentifiée, API, `/login`, 302 et 401 : `Cache-Control: no-store`
  → plus de réaffichage du board depuis bfcache / restauration d'onglet
  après expiration ou logout.
- `/style.css`, `/app.js`, `/static/*` : inchangés, revalidation par ETag.
- Onglet resté ouvert puis action API : modale « Session expirée » explicite.

### Garde-fous

- `pdm run check` : exit 0 — mypy 0 erreur, interrogate 100 %, ruff OK,
  vitest 81 passed, vite build OK, pytest 703 passed.
- Non committé (en attente de demande).
---

[← retour à backend/auth](index.md) · [voir log](../../log/2026-11-13.md)
