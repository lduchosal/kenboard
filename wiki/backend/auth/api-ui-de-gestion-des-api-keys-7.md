---
id: 7
title: "API / UI de gestion des API keys"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:28:58
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #7 — API / UI de gestion des API keys

Page d'administration des API keys (UI) — implémentée.

Livrée dans la même release que #6 (décision Q : tout en une release).

## Livraisons

- `templates/admin_keys.html` : table éditable calquée sur `admin_users.html`
  - Colonnes : Label, Statut (active/expirée/révoquée), Créée, Dernière utilisation, Expire, Scopes, Actions
  - Statut calculé à l'affichage (badge coloré : vert/orange/rouge)
  - Édition inline : label, expires_at (YYYY-MM-DDTHH:MM), scopes (paire `(project, level)` répétable avec + ajouter / × supprimer)
  - Bouton **Créer** ouvre une modale qui affiche la clé en clair UNE SEULE FOIS dans une textarea readonly. Bouton "Compris" reload la page.
  - Bouton **Révoquer** passe par le `confirm-modal` partagé
- `routes/pages.py` : nouvelle route `GET /admin/keys` qui charge `api_keys` + scopes via les nouvelles queries
- `partials/header.html` : ajout du lien "Clés API" dans le menu déroulant de l'avatar à côté de "Utilisateurs"

## Auth de la page

Décision Q : « on gère l'auth des users plus tard ». La page reste **ouverte** comme `/admin/users` actuellement, jusqu'à ce que #1 (web user auth) soit fait. À ce moment-là, les deux pages seront protégées par le même mécanisme de session.

## Tests

`tests/e2e/test_admin_keys.py` — **4 tests Playwright** :
- `test_page_loads_empty` : page rendue, table vide, add row visible
- `test_create_key_shows_plaintext_modal` : POST → modale visible avec clé `kb_...`
- `test_create_then_list` : après reload, la nouvelle clé apparaît avec son label
- `test_revoke_key` : révocation via confirm-modal, badge "révoquée" visible après reload

## État

Voir #6 pour le récap global. Prêt pour publish 0.1.16.
---

[← retour à backend/auth](index.md) · [voir log](../../log.md)
