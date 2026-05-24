---
id: 79
title: "QUALITY / Sonar - app.js modernisation"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:21
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/js
section_title: "JS modules"
---

# #79 — QUALITY / Sonar - app.js modernisation

18 issues SonarCloud sur le frontend JS:

- 10x javascript:S7764 (Prefer globalThis over window) — app.js lignes 14, 148, 156, 234, 242, 331, 335, 343, 418, 510
- 5x javascript:S2486 (Handle this exception or don't catch it at all) — app.js:36, 372 + admin_users.html:72, 85, 107
- 2x javascript:S7735 (Unexpected negated condition) — app.js:190, 486
- 1x javascript:S6582 (Prefer optional chain expression) — app.js:27

Fix:
- window.X → globalThis.X partout
- catch(e) {} vide → soit logger l'erreur (console.error/log structuré), soit retirer le try/catch
- Inverser les conditions négatives quand l'arborescence if/else l'autorise
- Utiliser ?. au lieu de && pour le chaînage optionnel
---

[← retour à frontend/js](index.md) · [voir log](../../log.md)
