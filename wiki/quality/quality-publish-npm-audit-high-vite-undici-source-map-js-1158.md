---
id: 1158
title: "quality / publish: npm audit high (vite, undici, source-map-js)"
status: done
who: "Claude"
due_date: 
updated_at: 2026-10-30T10:05:09
classified_at: 2026-10-30T10:03:30
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #1158 — quality / publish: npm audit high (vite, undici, source-map-js)

**TL;DR** — `publish.sh` cassait à l'étape 17 (npm audit : 3 high sur vite, undici, source-map-js) → `npm audit fix` + plancher vite remonté à `^8.3.5` ; 0 vulnérabilité.

publish.sh step 17 (JS Security Audit) échoue : 3 high — source-map-js 1.0.0-1.2.1 (GHSA-68fv-2mgg-jv7q), undici 8.0.0-8.12.1 (GHSA-4qv8-2p9j-2685, GHSA-f72v-6w45-q472, GHSA-xjj6-f33q-929c), vite 8.3.0-8.3.2 (launch-editor + 5 GHSA). Fix: npm audit fix / bump floors.

## Résolution

### Modifications
- `package-lock.json` — `npm audit fix` : vite 8.3.1 → 8.3.5, undici 8.11.2 → 8.12.3 (via jsdom), source-map-js 1.2.1 → 1.2.2 (via postcss/css-tree/magicast).
- `package.json` — plancher `vite` `^8.3.1` → `^8.3.5` (ratchet : on remonte le plancher, pas de borne haute). undici/source-map-js sont transitives, le lock suffit.

### Comportements obtenus
- `npm audit` : found 0 vulnerabilities.

### Garde-fous
- `npm test` (vitest) : 81/81 passed.
---

[← retour à quality](index.md) · [voir log](../log/2026-10-30.md)
