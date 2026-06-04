---
id: 189
title: "SEC / Masquer les détails de validation Pydantic en prod"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:43
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #189 — SEC / Masquer les détails de validation Pydantic en prod

Les erreurs Pydantic 422 retournent actuellement les détails champ par champ (app.py:156). En production, ne retourner qu'un message générique et logger les détails côté serveur uniquement.

---

## Résolution

### Modifications

- `src/dashboard/app.py` — le handler `ValidationError` ne retourne les `details` que si `debug=True` ; en prod, seul le message générique `{"error": "Validation error"}` est renvoyé (les détails restent dans les logs serveur via `log.warning`)

### Comportements obtenus

- En production : réponse 422 avec `{"error": "Validation error"}` uniquement
- En debug : réponse 422 avec `{"error": "Validation error", "details": [...]}` (comportement existant)
- Les détails de validation sont toujours loggés côté serveur dans les deux cas

### Garde-fous

- `pdm run test-quick` : 269 passed
---

[← retour à backend/auth](index.md) · [voir log](../../log/2026-05-24.md)
