---
id: 526
title: "EXTENSION / annotations - phase 6 drawer + push markdown vers kenboard"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-30T00:37:06
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: extension
section_title: "Browser extension"
---

# #526 — EXTENSION / annotations - phase 6 drawer + push markdown vers kenboard

Phase 6 (drawer + push markdown vers kenboard)

---

**Source (epic):** #520

## Résolution — openDrawer()/closeDrawer() + renderDrawer() : header (titre + URL canonique + count + ✕), liste avec quote tronquée 3 lignes + bouton 🗑 par item, footer avec bouton 'Pousser sur kenboard'. pushToKenboard() : charge baseUrl/apiToken/projectId depuis chrome.storage.local (réutilise la config existante), buildMarkdown() compose le markdown (Source link + blockquotes + [citer](URL#:~:text=…)), POST /api/v1/tasks avec credentials:'omit' + Bearer (même chemin auth que popup.js → évite le CSRF cookie). Sur succès : remplace le bouton par 'Vider / Garder pour itérer'.



## Garde-fous (partagés)

- pdm run build-extension : OK (bundle 113 KB IIFE).
- node --check sur le bundle : OK.
- web-ext lint : 0 erreur, 0 warning.
- pdm run js-test : 68 passed (63 existants + 5 nouveaux buildMarkdown).
- pdm run js-lint (Biome, scope src/dashboard) : clean.
- NON testé en navigateur ici (impossible d.exécuter MV3 dans cet environnement). À valider end-to-end sur Firefox release après reload de l.extension : Alt+K active, surligner persiste, push crée bien une tâche avec [citer](URL#:~:text=…).
---

[← retour à extension](index.md) · [voir log](../log.md)
