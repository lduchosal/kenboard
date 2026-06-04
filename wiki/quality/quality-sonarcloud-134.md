---
id: 134
title: "QUALITY / Sonarcloud"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:39
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #134 — QUALITY / Sonarcloud

https://sonarcloud.io/project/overview?id=lduchosal_kenboard
revue des issues, correction

---

## Résolution

### Passe 1 (v0.1.35) — 3 issues initiales

1. **`javascript:S1874`** — `app.js:276` — suppression du fallback `document.execCommand('copy')` (deprecated, les browsers modernes supportent tous `navigator.clipboard`).
2. **`python:S4502`** — `app.py:31` — faux positif CSRF. Ajout d'un commentaire expliquant la stratégie Origin/Referer + annotation `# NOSONAR`.
3. **`python:S3752`** — `auth_user.py:242` — split de la route `/login` en deux fonctions : `login()` GET-only (render form) et `login_post()` POST-only (validate credentials, rate-limited).

### Passe 2 (v0.1.40+) — 4 issues post-OIDC

4. **`python:S7632`** — `app.py:40` — syntaxe `# NOSONAR(python:S4502)` invalide → corrigée en `# NOSONAR — CSRF via Origin/Referer check`. Corrige aussi le hotspot `python:S4502` qui restait TO_REVIEW à cause de la mauvaise syntaxe.
5. **`python:S1192`** — `auth_oidc.py` — littéral `"login.html"` dupliqué 3× → extrait en constante `_LOGIN_TEMPLATE`.
6. **`python:S1192`** — `auth_user.py` — idem, même constante `_LOGIN_TEMPLATE`.
7. **`python:S8370`** — `auth_user.py:278` — `request.args.get("next")` utilisé dans un handler POST → retiré. Le `next` est lu uniquement depuis `request.form.get("next")` (le hidden field du formulaire de login porte la valeur).

### Hotspot

- **`python:S4502`** — CSRF hotspot sur `Flask(__name__, ...)`. Résolu par la combinaison du commentaire inline (stratégie documentée) + annotation `# NOSONAR` avec la bonne syntaxe. Si Sonar ne le supprime pas automatiquement, le marquer "Safe" dans l'UI avec la justification : *"CSRF protected via Origin/Referer same-host check in auth.py, tested in tests/unit/test_csrf.py"*.

### Garde-fous

- 263 tests unitaires/intégration verts après chaque passe
- Aucun changement de comportement utilisateur (les fixes sont du refactoring interne + suppression de code mort)
- `pdm run check` complet vert
---

[← retour à quality](index.md) · [voir log](../log/2026-05-24.md)
