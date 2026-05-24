---
id: 140
title: "SEC / Onboarding / XSS reflected data (S5131)"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:41
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #140 — SEC / Onboarding / XSS reflected data (S5131)

Sonar BLOCKER: la route /onboard reflète cat_id et project_id non sanitizés dans la réponse text/plain. Sanitizer les inputs avant interpolation.
---

[← retour à backend/auth](index.md) · [voir log](../../log.md)
