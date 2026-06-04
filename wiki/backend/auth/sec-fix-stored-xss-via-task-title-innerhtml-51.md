---
id: 51
title: "SEC / FIX / Stored XSS via task.title (innerHTML)"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:20
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #51 — SEC / FIX / Stored XSS via task.title (innerHTML)

**Sévérité: HIGH**

`task.title` est stocké brut (Pydantic ne valide que la longueur). Plusieurs vues côté JS construisent les cartes de tâches via template literal et `innerHTML` — un titre malicieux est rendu en HTML.

**Vector:** `POST /api/v1/tasks {"title": "<img src=x onerror=alert(1)>", ...}`

**Reproduction:** `python pentest/auth_xss_stored.py`

**Remédiation:** identique à #41+ (CSP + textContent au lieu d'innerHTML pour les titres). Idéalement: validateur Pydantic qui rejette `<` / `>` dans `title`.
---

[← retour à backend/auth](index.md) · [voir log](../../log/2026-05-24.md)
