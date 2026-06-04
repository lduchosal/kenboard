---
id: 82
title: "QUALITY / Sonar - cleanup Python divers"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:22
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #82 — QUALITY / Sonar - cleanup Python divers

4 issues Python éparses, à régler en bloc:

- python:S1192 (CRITICAL) routes/users.py:77 — Define a constant instead of duplicating "Not found" 3 times. Constante NOT_FOUND_ERROR ou réutilisation.

- python:S6863 (BUG) auth_user.py:284 — Specify an explicit HTTP status code for this error handler. Le @bp.errorhandler doit retourner un tuple avec status code explicite.

- python:S7632 (×2) ken.py:364, 397 — Fix issue suppression comment syntax. Probablement des "noqa"/"type: ignore" mal formés à corriger.
---

[← retour à quality](index.md) · [voir log](../log/2026-05-24.md)
