---
id: 250
title: "BUILD / JS / Validate"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:47
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/js
section_title: "JS modules"
---

# #250 — BUILD / JS / Validate

Superseded by #251 — 'js validate' is covered by Biome lint + tsc --noEmit in the new toolchain.

Original: J'ai vu la commande node -c src/dashboard/static/app.js 2>&1 && echo "JS OK". J'aimerai bien l'intégrer dans le processus de build pour s'asssurer que tous les JS sont valides. pdm validate js, sh publish.sh. Analyser quel est le meilleur outil pour le JS.
---

[← retour à frontend/js](index.md) · [voir log](../../log/2026-05-24.md)
