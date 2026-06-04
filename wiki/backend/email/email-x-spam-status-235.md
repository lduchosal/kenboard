---
id: 235
title: "EMAIL / X-Spam-Status"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:57
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/email
section_title: "Email & notifications"
---

# #235 — EMAIL / X-Spam-Status

L'email arrive en spam (score 6.2, seuil 4.5). Principaux tests SpamAssassin penalisants : MISSING_DATE (+1.36), MISSING_MID (+0.5), DOS_BODY_HIGH_NO_MID (+3.5).

---

## Resolution

Ajout des headers `Date` et `Message-ID` dans `src/dashboard/email.py`.

- `Date` : via `email.utils.formatdate(localtime=True)` — corrige MISSING_DATE (-1.36)
- `Message-ID` : via `email.utils.make_msgid()` avec le domaine extrait de SMTP_FROM — corrige MISSING_MID (-0.5) et DOS_BODY_HIGH_NO_MID (-3.5)

Score attendu apres fix : ~1.3 (sous le seuil de 4.5). Les tests NUMERIC_HTTP_ADDR et WEIRD_PORT sont lies a l'URL 127.0.0.1:5001 et disparaitront en prod.

### Garde-fous

- pytest unit : 343 passed
- mypy : clean
- flake8 : clean
---

[← retour à backend/email](index.md) · [voir log](../../log/2026-05-24.md)
