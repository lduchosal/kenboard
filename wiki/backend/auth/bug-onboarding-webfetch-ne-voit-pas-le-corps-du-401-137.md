---
id: 137
title: "BUG / Onboarding / WebFetch ne voit pas le corps du 401"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:40
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #137 — BUG / Onboarding / WebFetch ne voit pas le corps du 401

Quand Claude utilise WebFetch sur un lien onboarding, le tool reçoit le HTTP 401 mais **ne renvoie pas le corps de la réponse** (le runbook text/plain). Claude ne voit donc rien d'utile.

## Solution retenue

Créer une **route dédiée** qui retourne toujours **200** text/plain, sans auth :

```
GET /onboard/cat/<cat_id>/project/<project_id>
```

- Pas d'authentification sur cette route (c'est le runbook public)
- Retourne 200 text/plain avec le runbook onboarding
- Les deux IDs (cat + project) sont dans le path → plus besoin du fragment `#` que le serveur ne voit jamais
- Le bouton copy-onboard-link génère cette URL au lieu de `/cat/<id>.html?onboard#<project_id>`

## CSS : bouton toujours visible

Le bouton "Copy onboard link" est actuellement en `opacity: 0` et n'apparaît qu'au hover du `.section-title`. Il doit être **toujours visible** (pas caché derrière un hover) car c'est un point d'entrée important pour les agents.

## Étapes

1. Nouvelle route : `GET /onboard/cat/<cat_id>/project/<project_id>` → 200 text/plain
2. Exclure du middleware auth (pas dans `/api/v1/*`, pas de `@login_required`)
3. Mettre à jour `app.js:copyOnboardLink()` pour générer la nouvelle URL
4. **CSS** : rendre `.section-onboard-btn` toujours visible (`opacity: 1` par défaut)
5. Garder le 401 existant sur `/cat/<id>.html` pour rétrocompat
6. Tests unit
7. Enchaîner avec #138 (réécriture du contenu du runbook)

## Acceptation

- `curl https://kenboard.example.com/onboard/cat/<cat_id>/project/<project_id>` → 200
- WebFetch sur la même URL → Claude voit le runbook complet
- Le bouton copy-onboard-link est **toujours visible** dans l'UI (pas de hover nécessaire)
- Le flow browser sur `/cat/<id>.html` n'est pas affecté
---

[← retour à backend/auth](index.md) · [voir log](../../log.md)
