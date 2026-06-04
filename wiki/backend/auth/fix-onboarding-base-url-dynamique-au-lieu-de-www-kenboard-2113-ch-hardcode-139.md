---
id: 139
title: "FIX / Onboarding / base_url dynamique au lieu de www.kenboard.2113.ch hardcodé"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:41
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #139 — FIX / Onboarding / base_url dynamique au lieu de www.kenboard.2113.ch hardcodé

Le runbook onboarding hardcode `base_url=https://www.kenboard.2113.ch` dans le fichier .ken proposé. Si kenboard est self-hosted sur un autre domaine, l'agent reçoit une URL incorrecte.

## Solution

Utiliser `request.host_url` (qui respecte ProxyFix / X-Forwarded-Proto) pour dériver le `base_url` dynamiquement dans la route `/onboard/cat/<cat_id>/project/<project_id>`. Le runbook affiche alors l'URL réelle du serveur qui sert la réponse.

Mettre aussi à jour les variantes 401 (`onboarding_text` et `onboarding_json`) pour qu'elles utilisent la même logique.

## Acceptation

- Un kenboard self-hosted sur `https://board.example.com` génère `base_url=https://board.example.com` dans le runbook
- Aucun hardcode de `www.kenboard.2113.ch` ne subsiste dans onboarding.py
---

[← retour à backend/auth](index.md) · [voir log](../../log/2026-05-24.md)
