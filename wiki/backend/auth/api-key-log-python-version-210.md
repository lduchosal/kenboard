---
id: 210
title: "API KEY / Log python version"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:48
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #210 — API KEY / Log python version

Log python version dans les API keys.

---

## Résolution

Implémenté conjointement avec #209 (même migration).

### Modifications

- `ken.py` — User-Agent enrichi : \`ken/<version> Python/<version>\` (ex. \`ken/0.1.65 Python/3.13.3\`) au lieu du défaut \`Python-urllib/3.13\`
- `auth.py` — capture du User-Agent dans \`_touch_last_used()\`, stocké dans \`api_keys.last_used_agent\`
- `templates/admin_keys.html` — colonne "Agent" affichant les 30 premiers caractères + title au hover

### Analyse sécurité (spoofing / injection)

Le User-Agent est 100% contrôlé par le client. Un agent malveillant peut envoyer n'importe quoi, y compris du HTML/JS. Pas de risque d'injection car :
- **Auto-escape Jinja2** sur toutes les expressions `{{ }}` (pas de `|safe`)
- **`title` attribut** protégé par l'escape des `"` en `&quot;`
- **Troncation** `[:200]` avant écriture DB, `[:30]` à l'affichage
- **Queries paramétrées** — pas de SQL injection

### Comportements obtenus

- L'admin voit quel client et quelle version Python utilise chaque clé
- La colonne Agent affiche ex. \`ken/0.1.65 Python/3.13.3\` ou le User-Agent brut d'un autre client HTTP

### Garde-fous

- `pdm run check` → 321 passed, tout vert
---

[← retour à backend/auth](index.md) · [voir log](../../log.md)
