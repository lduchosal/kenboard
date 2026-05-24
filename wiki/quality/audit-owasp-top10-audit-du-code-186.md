---
id: 186
title: "AUDIT / OWASP TOP10 / Audit du code"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:41
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #186 — AUDIT / OWASP TOP10 / Audit du code

Audit de sécurité style OWASP TOP10

---

## Résolution

### Audit OWASP Top 10

| # | Catégorie | Verdict | Notes |
|---|-----------|---------|-------|
| A01 | Broken Access Control | OK | Multi-couche : middleware auth, scopes API keys par projet, vérif ownership password |
| A02 | Cryptographic Failures | OK | Argon2 pour mots de passe, SHA256 pour API keys, SECRET_KEY obligatoire en prod |
| A03 | Injection (SQL + XSS) | OK | Requêtes paramétrées aiosql, Jinja2 autoescape, DOMPurify, regex NO_ANGLE_BRACKETS |
| A04 | Insecure Design | OK | API keys hashées, PKCE/S256 pour OIDC, secrets.token_urlsafe |
| A05 | Security Misconfiguration | OK | CSP, X-Frame-Options DENY, HSTS, nosniff, Server header masqué |
| A06 | Vulnerable Components | OK | Deps à jour : Flask 3.1.3, PyMySQL 1.1.2, Authlib 1.6.10 |
| A07 | Auth Failures | OK | Argon2, rate limiting login 5/min 20/h, session nonce, cookies Secure+HttpOnly+SameSite |
| A08 | CSRF | OK | Validation Origin/Referer sur méthodes unsafe, Bearer tokens exemptés |
| A09 | Logging | GAPS | Pas de log pour login success/failure, logout, actions admin CRUD |
| A10 | SSRF | OK | Aucun endpoint n'accepte d'URL user pour des requêtes server-side |

### Points d'attention (non critiques)

1. **A09 — Logging incomplet** : pas de log pour login success/failure, logout, actions admin (CRUD users, API keys)
2. **Rate limiting limité au login** : manquant sur /api/v1/keys, /api/v1/users/<id>/reset-password
3. **Détails de validation exposés** : erreurs Pydantic 422 retournent les détails champ par champ

### Conclusion

Posture de sécurité solide. Les vulnérabilités historiques (XSS, CSRF bypass, open redirect) corrigées lors des audits précédents (tâches 34, 36, 40-56). Gaps restants sur le logging des événements d'authentification — important pour la détection d'intrusion mais pas une vulnérabilité exploitable.
---

[← retour à quality](index.md) · [voir log](../log.md)
