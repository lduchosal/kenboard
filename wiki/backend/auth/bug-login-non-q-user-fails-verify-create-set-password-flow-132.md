---
id: 132
title: "BUG / Login non-Q user fails / verify create + set password flow"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:38
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #132 — BUG / Login non-Q user fails / verify create + set password flow

Q rapporte qu'il a des users dans la base (ex: user@example.com) avec un mot de passe, mais l'écran de login retourne "Identifiants invalides".

---

## Résolution

### Cause racine

Le panneau `/admin/users` propose un champ "Mot de passe" sur chaque ligne de user existant. Quand l'admin remplit ce champ et clique "Enregistrer", le JS `saveUser()` envoyait `password` dans le **PATCH** `/api/v1/users/<id>`. Or le modèle Pydantic `UserUpdate` (`src/dashboard/models/user.py:17`) a `extra="ignore"` et **ne contient pas** de champ password — c'est intentionnel (cf. #53, défense contre mass-assignment + le test `test_patch_ignores_password_field` qui le vérifie explicitement).

Conséquence user-visible : le PATCH retourne 200 OK, le JS recharge la page, l'admin croit avoir mis à jour le mot de passe — mais le `password_hash` en DB n'a jamais bougé. La prochaine tentative de login échoue avec "Identifiants invalides".

Le bug n'a rien à voir avec :
- Le name contenant un `@` (testé : login fonctionne pour `user@example.com` dès lors que le password_hash est correct)
- Q vs autre user (pas de hardcoding de Q nulle part dans la chaîne d'auth)
- ModSec ou le reverse proxy (le PATCH passe correctement, c'est juste son contenu qui est filtré côté Pydantic)

### Modifications

- **`src/dashboard/templates/admin_users.html`** — `saveUser()` enchaîne maintenant un appel à `POST /api/v1/users/<id>/reset-password` après le PATCH lorsque le champ password est rempli. Cet endpoint admin-only (déjà présent depuis #53, géré par `reset_password` dans `src/dashboard/routes/users.py:139`) hash le mot de passe en argon2 et applique la contrainte ≥ 8 caractères. Commentaire JS ajouté pour expliquer pourquoi PATCH ne suffit pas.
- **`tests/unit/test_auth_user.py`** — 3 nouveaux tests dans `TestLoginFlow` :
  - `test_login_works_for_email_named_user` : confirme que login marche pour n'importe quel name (y compris contenant `@`) tant que le password_hash est posé.
  - `test_admin_ui_patch_password_silently_dropped` : **reproduit** exactement la séquence user-facing — admin Q crée un user via POST sans password, PATCHe avec un champ password, déconnecte Q, tente login en tant que ce user → 200 + "Identifiants invalides". Sert de garde-fou contre toute régression similaire (ex: si quelqu'un retire le commentaire JS et envoie à nouveau password dans le PATCH).
  - `test_admin_reset_password_endpoint_enables_login` : valide la voie correcte — admin POST `/reset-password` puis login en tant que ce user → 302 succès. C'est ce que le JS fait maintenant.

### Comportements obtenus

- Le panneau `/admin/users` peut maintenant **réellement** définir/réinitialiser le mot de passe d'un autre user via le champ inline.
- Si le mot de passe saisi fait < 8 caractères, le `POST /reset-password` retourne 422, l'`apiCall` JS affiche une popup "Validation", l'admin sait qu'il doit saisir plus long. C'était silencieusement perdu avant.
- Le test `test_patch_ignores_password_field` continue de passer : le contrat backend (PATCH ne touche jamais au mot de passe, c'est intentionnel) reste inchangé.
- 244 tests unitaires verts (+3 vs baseline).

### Garde-fous

- `pdm run check` (composite isort, format, docformatter, typecheck, flake8, interrogate, refurb, lint, vulture, test-quick) → ✅ vert.
- Aucun changement de schéma DB, pas de migration.
- Aucun changement d'API publique : `PATCH /api/v1/users/<id>` continue de drop `password` silencieusement, c'est juste le client (JS du panneau admin) qui sait maintenant qu'il doit faire un appel séparé.
- Le seul fichier touché côté runtime est un template HTML (`admin_users.html`) — pas d'impact sur les autres pages.

### Étapes opérateur (côté Q)

1. Pull la nouvelle version sur web2.
2. Restart kenboard.
3. Aller sur `/admin/users`, taper le mot de passe dans la ligne `user@example.com`, cliquer Enregistrer.
4. Le mot de passe est cette fois réellement écrit en DB. Le user peut se loguer.

### Hors scope

- Réécrire l'UI `/admin/users` (passer à un modal dédié pour le mot de passe au lieu du champ inline). Le fix actuel est minimal et préserve l'ergonomie existante.
- Ajouter un endpoint `PATCH` qui accepterait `password` : volontairement pas fait, le séparer reste la bonne décision sécurité (cf. modèle `UserUpdate`).
---

[← retour à backend/auth](index.md) · [voir log](../../log.md)
