---
id: 54
title: "SEC / FIX / Session non invalidée après logout"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:17
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #54 — SEC / FIX / Session non invalidée après logout

**Sévérité: HIGH** — corrigé.

## Cause racine

Flask utilise des sessions signées (cookie côté client). Le serveur ne peut pas révoquer un cookie unilatéralement sans backend de sessions. `logout_user()` ne fait que supprimer le cookie côté client; un cookie capturé avant le logout reste valide jusqu'à expiration ou rotation du `KENBOARD_SECRET_KEY`.

## Fix

Approche "per-user nonce embarqué dans l'identifiant Flask-Login".

1. **Migration `0008.add_user_session_nonce.sql`** — ajoute `users.session_nonce CHAR(32) NOT NULL DEFAULT ''` (avec rollback).
2. **`queries/users.sql`** — `usr_get_by_id` et `usr_get_by_name` retournent `session_nonce`. Nouvelle query `usr_rotate_session_nonce`.
3. **`auth_user.py`**:
   - `CurrentUser` stocke `session_nonce` et override `get_id()` pour retourner `"<uuid>:<nonce>"`. Cette chaîne va dans le cookie de session signé.
   - `_load_user(packed_id)` parse, fetch le user, **refuse si le nonce ne correspond pas** au DB. C'est le point de blocage qui fait le travail.
   - `_rotate_session_nonce(user_id)` génère un nouveau hex(16) et le persiste.
   - `/logout` appelle `_rotate_session_nonce(current_user.id)` AVANT `logout_user()`. Tous les cookies déjà émis (y compris `remember_token`) deviennent immédiatement non-vérifiables.
   - `/login` seed un nonce sur les users qui n'en ont pas encore (back-fill pour les comptes pré-existants), mais ne le rotate PAS sur re-login (sinon multi-device casse).
4. **`conftest.py`** — schéma test mis à jour + back-fill pour les DB carry-over.

## Vérification

- `pdm run test-quick` → 205 passed (7 nouveaux + 198 existants)
- `python pentest/auth_session.py` → 0 finding (avant: 1 HIGH "Session non invalidée")
- `pdm run check` → vert

`tests/unit/test_logout_invalidates.py` (nouveau, 7 tests):
- login seed un nonce non vide
- /logout rotate le nonce en DB
- replay d'un cookie pré-logout → redirect /login
- re-login après /logout fonctionne
- re-login en parallèle ne rotate PAS le nonce (multi-device intact)
- rotation out-of-band (admin/cron) → tous les sessions invalidées

`pentest/auth_session.py` converti en regression test.

## Limitations

Cette approche n'invalide pas les sessions individuelles d'un même user — `/logout` déconnecte le user de TOUS ses appareils. C'est volontaire et plus sûr (un attaquant qui a volé un cookie ne peut pas s'isoler de la victime). Pour une déconnexion par-device, il faudrait stocker un nonce par session côté DB (table `user_sessions`).
---

[← retour à backend/auth](index.md) · [voir log](../../log/2026-05-24.md)
