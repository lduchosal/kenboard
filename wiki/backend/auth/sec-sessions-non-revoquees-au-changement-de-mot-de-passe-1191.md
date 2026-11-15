---
id: 1191
title: "SEC / Sessions non révoquées au changement de mot de passe"
status: done
who: "Claude"
due_date: 
updated_at: 2026-11-15T19:37:09
classified_at: 2026-11-15T18:45:14
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #1191 — SEC / Sessions non révoquées au changement de mot de passe

**TL;DR** — Un cookie volé restait valide après un changement de mot de passe (self-service ou reset admin) → le `session_nonce` est tourné dans les deux cas.

---

Issu de l'audit #1183 (M3). Ni le changement self-service ni le reset admin (routes/users.py) ne tournent le session_nonce : un cookie volé reste valide après changement de mot de passe.

---

## Résolution

### Modifications

- `src/dashboard/auth_session.py` — `revoke_sessions(user_id, keep_current=…)` : rotation du nonce, puis réémission de la session courante si demandé.
- `src/dashboard/routes/users.py` — appelé par `change_password` (`keep_current=True`) et `reset_password` (`keep_current=False`).
- `doc/architecture.md`, `doc/authentication.md` — colonne `session_nonce` mise à jour.
- `tests/unit/test_sec_audit.py::TestPasswordChangeRevokesSessions` — 2 tests.

### Comportements obtenus

- Changement self-service : les autres sessions répondent 401, l'onglet qui a changé le mot de passe reste connecté.
- Reset par un admin : toutes les sessions de la cible tombent, celle de l'admin est intacte.

### Garde-fous

- `pdm run check` : exit 0 — isort, black, docformatter, mypy strict, flake8, interrogate 100 %, refurb, ruff, vulture, biome, tsc, vitest, build Vite, 817 tests hors e2e, gate métriques PASS.
- `pdm run test-cov` (e2e inclus) : 867 passés, 2 échecs **pré-existants** et sans rapport (`TestLoginRateLimit`, dépendance d'ordre avec les e2e, reproduits sur HEAD intact — ticket #1196). Couverture 96,15 %, `pdm run metrics-gate` PASS.
- Non commité : les modifications sont dans l'arbre de travail, en attente de revue.
---

[← retour à backend/auth](index.md) · [voir log](../../log/2026-11-15.md)
