---
id: 209
title: "API KEYS / Log IP"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:47
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #209 — API KEYS / Log IP

Dans la fenêtre des clés d'API, on voit la date de dernière utilisation. Il faudrait ajouter l'adresse IP depuis laquelle cette clé à été utilisée. Attention aux reverses proxy.

---

## Résolution

Implémenté conjointement avec #210 (même migration, mêmes fichiers).

### Modifications

- `migrations/0017.add_api_key_usage_metadata.sql` — ajout colonnes `last_used_ip VARCHAR(45)` et `last_used_agent VARCHAR(200)` à `api_keys` (idempotent)
- `queries/api_keys.sql` — `key_touch_last_used` enrichi avec `:ip` et `:agent`; SELECTs mis à jour
- `auth.py` — `_touch_last_used()` capture `request.remote_addr` (résolu par ProxyFix via X-Forwarded-For) et `request.user_agent.string`
- `models/api_key.py` — champs `last_used_ip`, `last_used_agent` sur `ApiKey`
- `templates/admin_keys.html` — 2 nouvelles colonnes "IP" et "Agent" (agent tronqué à 30 chars, title complet au hover)
- `tests/conftest.py` — miroir schéma + backfill

### Analyse sécurité (spoofing / injection)

**Spoofing** :
- **User-Agent** : 100% contrôlé par le client, trivial à spoofer. Ce sont des données de traçabilité indicatives, pas des données de confiance.
- **IP** : ProxyFix(`x_for=1`) ne trust qu'un seul hop nginx. Tant que nginx fait `proxy_set_header X-Forwarded-For $remote_addr;`, le client ne peut pas spoofer l'IP vue par le serveur.

**XSS / HTML / JS injection** : **non vulnérable**.
- Jinja2 auto-escape activé par défaut (templates `.html`), aucun `|safe` sur ces valeurs → `<script>alert(1)</script>` est rendu en `&lt;script&gt;...`
- L'attribut `title="..."` est aussi protégé : Jinja2 escape `"` en `&quot;`
- SQL injection impossible : queries paramétrées (`:ip`, `:agent`)
- Troncation défensive : `[:200]` côté Python avant écriture DB, `[:30]` côté template

### Comportements obtenus

- L'admin voit l'IP source de la dernière utilisation de chaque clé
- ProxyFix (configuré dans app.py) résout l'IP réelle derrière nginx
- Un User-Agent malveillant s'affiche en texte brut, pas d'exécution

### Garde-fous

- `pdm run check` → 321 passed, tout vert
---

[← retour à backend/auth](index.md) · [voir log](../../log.md)
