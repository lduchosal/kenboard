---
id: 525
title: "EXTENSION / annotations - phase 5 highlight rendering + persistance par URL canonique"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-30T00:37:05
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: extension
section_title: "Browser extension"
---

# #525 — EXTENSION / annotations - phase 5 highlight rendering + persistance par URL canonique

Phase 5 (highlight rendering + persistance + SPA)

---

**Source (epic):** #520

## Résolution — wrapRange(range, id) : TreeWalker text-only sur le common ancestor, split de la première/dernière node text si besoin, wrap chaque node dans un <span class=kb-hl data-kb-id=N>. Skip si dans notre shadow ou dans une span kb-hl existante. quoteFromRange + posFromRange (dom-anchor-text-quote/-position) → {quote, position} stockés dans chrome.storage.local sous kb_anno:<canonicalUrl>. canonicalUrl() prend <link rel=canonical> puis fallback location.origin+pathname+search, et strip utm_*, mc_*, fbclid, gclid, yclid. reapplyAll() au load + à chaque pushState/replaceState/popstate (patchHistory monkey-patche les deux et écoute popstate). onMaybeUrlChange() unwrap les highlights, vide annotations, recharge pour la nouvelle URL canonique.



## Garde-fous (partagés)

- pdm run build-extension : OK (bundle 113 KB IIFE).
- node --check sur le bundle : OK.
- web-ext lint : 0 erreur, 0 warning.
- pdm run js-test : 68 passed (63 existants + 5 nouveaux buildMarkdown).
- pdm run js-lint (Biome, scope src/dashboard) : clean.
- NON testé en navigateur ici (impossible d.exécuter MV3 dans cet environnement). À valider end-to-end sur Firefox release après reload de l.extension : Alt+K active, surligner persiste, push crée bien une tâche avec [citer](URL#:~:text=…).
---

[← retour à extension](index.md) · [voir log](../log/2026-05-30.md)
