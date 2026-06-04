---
id: 53
title: "SEC / FIX / Changement de mot de passe sans ancien"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:21
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #53 — SEC / FIX / Changement de mot de passe sans ancien

**Sévérité: HIGH**

`PATCH /api/v1/users/<id> {"password": "newpass"}` change le password sans demander l'ancien. Combiné à un XSS / CSRF / vol de session (tous présents par ailleurs), c'est un takeover trivial. Même sans attaque, c'est contre les bonnes pratiques (un attaquant qui s'empare d'une session ouverte 30s peut verrouiller l'utilisateur définitivement en changeant le mot de passe).

**Reproduction:** `python pentest/auth_mass_assignment.py`

**Remédiation:**
1. Séparer "changement de password" dans une route dédiée `POST /api/v1/users/<id>/password` qui exige `{old_password, new_password}` et qui vérifie l'ancien.
2. Retirer `password` du modèle `UserUpdate`.
3. Permettre à un admin de réinitialiser le password d'un autre user via `POST /api/v1/users/<id>/reset-password` (admin-only).
---

[← retour à backend/auth](index.md) · [voir log](../../log/2026-05-24.md)
