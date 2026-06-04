---
id: 45
title: "SEC / FIX / Headers de sécurité secondaires"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:17
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #45 — SEC / FIX / Headers de sécurité secondaires

**Sévérité: MEDIUM**

Headers manquants (en plus de CSP/X-Frame-Options déjà couverts par #41 et #42):

- `Strict-Transport-Security` (HSTS)
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: ()` (lockdown)
- `Cross-Origin-Opener-Policy: same-origin`
- `Cross-Origin-Resource-Policy: same-origin`

**Reproduction:** `python pentest/headers.py`

**Remédiation:** poser tous ces headers dans le même `@app.after_request` que la CSP (#41). HSTS doit être activé seulement quand l'app sait qu'elle tourne derrière HTTPS.
---

[← retour à backend/auth](index.md) · [voir log](../../log/2026-05-24.md)
