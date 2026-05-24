---
id: 178
title: "FIX / CLI / SSL certifi plug-and-play"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:40
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: cli/ken
section_title: "ken task CLI"
---

# #178 — FIX / CLI / SSL certifi plug-and-play

Python installe via python.org sur macOS n a pas de CA bundle. ken echouait avec SSL CERTIFICATE_VERIFY_FAILED. Fix : utiliser certifi.where() comme CA file dans le contexte SSL de urllib. certifi est une dep transitive (via requests) et se met a jour automatiquement avec pip upgrade.

---

## Resolution

- ken.py : nouveau helper _ssl_context() qui cree un ssl.create_default_context(cafile=certifi.where()). Fallback sur None si certifi absent. Le contexte est passe a urllib_request.urlopen(req, context=_SSL_CTX).
- Teste sur Python 3.12 python.org (cassait avant, fonctionne apres).
- 269 tests verts.
---

[← retour à cli/ken](index.md) · [voir log](../../log.md)
