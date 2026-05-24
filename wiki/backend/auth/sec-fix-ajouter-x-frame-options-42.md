---
id: 42
title: "SEC / FIX / Ajouter X-Frame-Options"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:09
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #42 — SEC / FIX / Ajouter X-Frame-Options

**Sévérité: HIGH**

Header `X-Frame-Options` absent → page embeddable dans une iframe → clickjacking possible (l'attaquant superpose un kanban dans une page piégée et fait cliquer l'utilisateur sur "Supprimer" sans qu'il s'en rende compte).

**Reproduction:** `python pentest/headers.py`

**Remédiation:** `X-Frame-Options: DENY` (ou `frame-ancestors 'none'` dans la CSP, déjà couvert par #41).
---

[← retour à backend/auth](index.md) · [voir log](../../log.md)
