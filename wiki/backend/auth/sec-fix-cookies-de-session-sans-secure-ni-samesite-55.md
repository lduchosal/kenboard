---
id: 55
title: "SEC / FIX / Cookies de session sans Secure ni SameSite"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:17
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #55 — SEC / FIX / Cookies de session sans Secure ni SameSite

**Sévérité: MEDIUM**

Les cookies posés par Flask-Login:

| Cookie | HttpOnly | Secure | SameSite |
|---|---|---|---|
| `remember_token` | ✓ | ✗ | Lax |
| `session` | ✓ | ✗ | (absent) |

**Reproduction:** `python pentest/auth_session.py`

**Remédiation:** dans `auth_user.py:init_login_manager`, ajouter:
```python
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = True   # ssi prod HTTPS
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["REMEMBER_COOKIE_SECURE"] = True  # déjà partiel
```
`SESSION_COOKIE_SECURE` doit être conditionné à un flag `KENBOARD_HTTPS=true` pour que le dev en HTTP continue de marcher.
---

[← retour à backend/auth](index.md) · [voir log](../../log/2026-05-24.md)
