---
id: 521
title: "EXTENSION / annotations - phase 1 scaffold build (esbuild + libs ancrage)"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-30T00:09:07
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: extension
section_title: "Browser extension"
---

# #521 — EXTENSION / annotations - phase 1 scaffold build (esbuild + libs ancrage)

Phase 1 — scaffold build : package.json deps (dom-anchor-text-quote, dom-anchor-text-position, esbuild devDeps), script npm build-extension, alias pdm, bundle stub extension/content/annotate.bundle.js committé. (cf. epic #520)

---

## Résolution

### Modifications
- package.json — devDeps : `dom-anchor-text-quote@^4.0.2`, `dom-anchor-text-position@^5.0.0` (les versions effectivement publiées par Hypothesis), `esbuild@^0.24.0`. Script `build-extension` : `esbuild extension/content/annotate.src.js --bundle --outfile=extension/content/annotate.bundle.js --target=chrome120,firefox142 --format=iife --legal-comments=external`.
- pyproject.toml — alias pdm `build-extension = { shell = "npm run build-extension" }`, dans la même zone que js-build.
- publish.sh — appel `run_command "pdm run build-extension" "Extension content bundle"` au début du bloc `if [ -d extension ]`, juste avant le zip → la release embarque toujours un bundle frais matchant la source committée + les deps pinnées.
- extension/content/annotate.src.js (nouveau) — stub Phase 1 : importe les deux libs d'ancrage et expose `window.__kbAnnotate = { phase: "1-scaffold", textQuote, textPosition }`. Le Phase 2 remplace tout le contenu par le vrai content script.
- extension/content/annotate.bundle.js (nouveau, committé) — bundle IIFE de 90 KB (l'essentiel du poids vient de diff-match-patch tiré par dom-anchor-text-quote pour le fuzzy anchoring).
- extension/content/annotate.bundle.js.LEGAL.txt (nouveau, committé) — attributions de licences extraites par esbuild.
- package-lock.json — refresh.

### Garde-fous
- `npm install` : OK (deps installés dans node_modules).
- `pdm run build-extension` : Done in 11ms, bundle 90 KB.
- `node --check extension/content/annotate.bundle.js` : syntax OK.
- `web-ext lint --source-dir extension` : 0 erreur, 0 warning.
- `sh -n publish.sh` : OK.
- Le bundle n'est pas encore référencé par manifest.json (Phase 2). Donc `web-ext lint` ne le charge pas — c'est attendu.

### À suivre
Phase 2 (#522) déclare `content_scripts` dans manifest.json et remplace le stub par le scaffold Shadow DOM.
---

[← retour à extension](index.md) · [voir log](../log/2026-05-30.md)
