---
id: 147
title: "CLI / ONBOARDING / mauvais protocole"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:37
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: cli/ken
section_title: "ken task CLI"
---

# #147 — CLI / ONBOARDING / mauvais protocole

Quand on onboard un agent, le protocole utilisé n'est pas celui de la URL onboarding quand on est derrière un reverse proxy pour le SSL.

Le .ken de configuration n'a pas le bon protocol HTTP au lieu de HTTPS

---

## Résolution

### Cause

`request.host_url` retourne `http://` quand nginx ne forwarde pas `X-Forwarded-Proto: https`. Le ProxyFix est en place côté Flask mais dépend de ce header. Sans lui, le runbook onboarding affiche `base_url=http://www.kenboard.2113.ch` au lieu de `https://`.

### Fix

Nouveau helper `derive_base_url()` dans `onboarding.py` qui :
1. Lit `request.host_url` (respecte ProxyFix quand le header est présent)
2. **Fallback** : si `Config.KENBOARD_HTTPS=true` ET l'URL commence par `http://`, force le schéma à `https://`

Les 3 callers qui dérivaient `base_url` manuellement (`onboard_route`, `_unauthorized`, `_enforce`) utilisent maintenant ce helper.

### Garde-fous

- 265 tests verts, `pdm run check` OK
- Aucun changement de comportement quand `KENBOARD_HTTPS=false` (dev local en HTTP)
---

[← retour à cli/ken](index.md) · [voir log](../../log.md)
