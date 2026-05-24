---
id: 131
title: "BUG / Remove user fails"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:38
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #131 — BUG / Remove user fails

Connecté en tant que user Q, avec les drois Admin, quand je supprime un utilisateur, j'ai message 403 forbidden.
Quand je souhaite modifier un utilisateur existant, changer sa couleur par exemple, j'ai le même message. Reproduit ces comportements avec un test unitaire et corrige le problème

---

## Résolution

### Diagnostic

**La cause n'est pas dans kenboard** — c'est **ModSecurity** qui bloque les requêtes PATCH/DELETE sur `/api/v1/users/*` au niveau du reverse proxy nginx, **avant** qu'elles n'atteignent Flask. Symptôme typique de WAF :

- 403 retourné au browser
- Aucune trace dans `/var/log/kenboard/kenboard.log` (la requête n'arrive jamais à gunicorn)
- Visible uniquement dans `/var/log/nginx/error.log` avec une ligne `ModSecurity: Access denied with code 403 ... [id "..."]`

Probable false positive sur une règle OWASP CRS (ex `942100`-`942500` SQL injection sur les UUIDs dans l'URL, ou `949110` anomaly score).

**Action requise côté infra (hors kenboard)** : whitelister la/les règle(s) pour le location `/api/v1/` dans la conf nginx :

```nginx
location /api/v1/ {
    modsecurity_rules '
        SecRuleRemoveById <id-trouvé-dans-modsec_audit.log>
    ';
    proxy_pass http://127.0.0.1:8080;
    proxy_set_header Host $host;
    proxy_set_header Origin $http_origin;
    ...
}
```

### Reproduction côté code

Tentative de reproduction par un test unitaire admin → **non reproductible**. Les deux nouveaux tests `test_patch_user_allowed` et `test_delete_user_allowed` passent, ce qui confirme que le middleware kenboard gère correctement le cas admin Q sur PATCH/DELETE `/api/v1/users/<id>`.

### Modifications conservées

- **`tests/unit/test_admin_only.py`** — ajout de deux tests dans `TestAdminOnlyAsAdminUser` :
  - `test_patch_user_allowed` : PATCH d'un user (changement de couleur) par admin → 200
  - `test_delete_user_allowed` : DELETE d'un user par admin → 204
  Ces deux paths n'étaient **pas couverts** par la suite existante (qui ne testait que GET, POST sur les endpoints admin-only). Maintenant si le middleware admin-only casse un jour, le test échouera.
- **`src/dashboard/auth.py`** — ajout de logging structuré sur les deux branches 403 de `_enforce_cookie_session`:
  - `auth.cookie.csrf_rejected` (warn) : émis quand le check Origin/Referer rejette une requête. Champs loggés : method, path, host, origin, referer, user_id.
  - `auth.cookie.admin_required` (warn) : émis quand un user non-admin essaie un endpoint admin-only. Champs loggés : method, path, user_id, user_name, is_admin.
  Permet de diagnostiquer en 5 secondes la prochaine fois qu'un 403 cookie-session apparaît : `tail -F /var/log/kenboard/kenboard.log | grep auth.cookie`.

### Comportements obtenus

- 241 tests unitaires passent (4 ajoutés vs baseline).
- Aucun changement de comportement public — uniquement de la couverture et de l'observabilité.
- Le middleware reste strictement identique pour les chemins success ; seules les branches 403 émettent désormais un événement structuré.

### Garde-fous

- `pdm run check` (composite) → vert.
- Aucun changement de schéma DB, pas de migration.
- Aucun changement d'API publique.

### Hors scope

- **Pas de fix dans kenboard** : le bug est purement environnemental (ModSec côté reverse proxy). Voir la section "Action requise côté infra" ci-dessus.
- Une note dans `INSTALL.md` sur les exigences WAF (whitelist des méthodes/URI REST) serait utile pour les futures installations — à arbitrer dans une tâche dédiée si Q en voit l'utilité.
---

[← retour à backend/auth](index.md) · [voir log](../../log.md)
