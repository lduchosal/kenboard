---
id: 141
title: "SEC / Login / Open redirect (S5146)"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:41
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #141 — SEC / Login / Open redirect (S5146)

Sonar BLOCKER: redirect basé sur next_url user-controlled dans login_post. Vérifier que _is_safe_url couvre le cas.
---

[← retour à backend/auth](index.md) · [voir log](../../log.md)
