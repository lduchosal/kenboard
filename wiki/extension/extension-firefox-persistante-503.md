---
id: 503
title: "EXTENSION / Firefox / Persistante"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-29T08:13:06
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: extension
section_title: "Browser extension"
---

# #503 — EXTENSION / Firefox / Persistante

Enregistrer l'extension Firefox de manière à ce quelle soit persistante dans le browser et pas seulement en exerimental debug que l'on doit reinstaller a chaque redemarrage

---

## Résolution

### Contexte technique
"Load Temporary Add-on" (about:debugging) est volatil : Firefox le retire à chaque redémarrage. Firefox **release** n'installe de façon permanente que des add-ons **signés par Mozilla**. La signature exige (a) un id d'extension stable dans le manifest et (b) un compte AMO + credentials API.

### Modifications
- extension/manifest.json — `browser_specific_settings.gecko` : id stable `kenboard-quick-task@2113.ch`, `strict_min_version = 142.0` (couvre options_page introduit en 126 ET data_collection_permissions introduit en 140/Android 142), et `data_collection_permissions: { required: ["none"] }` (déclare aucune collecte de données — exigé par AMO pour les nouvelles extensions).
- scripts/sign-firefox-extension.sh — wrapper `web-ext sign --channel unlisted` qui produit un .xpi signé. Placé dans scripts/ (PAS dans extension/) car extension/ est zippé tel quel dans la release : ni le script, ni les creds, ni les artefacts ne doivent s'y trouver. Source-dir = extension/, artifacts-dir = web-ext-artifacts/ (racine). web-ext tiré via `npx --yes` (pas ajouté à package.json).
- Credentials : lus depuis l'env (AMO_JWT_ISSUER/AMO_JWT_SECRET) ou un fichier gitignoré .amo-credentials à la racine — jamais en dur, jamais sur une ligne de commande, jamais dans le zip de release.
- extension/README.md — section "Firefox (persistent)" : flux signature AMO unlisted puis install via about:addons -> gear -> Install Add-on From File ; + fallback Developer Edition/Nightly/ESR (xpinstall.signatures.required=false).
- .gitignore — /web-ext-artifacts/ et /.amo-credentials (racine).

### Comportements obtenus
- Une fois signé en unlisted, le .xpi s'installe de façon permanente dans Firefox release et survit aux redémarrages.
- browser_specific_settings est ignoré par Chrome (sous gecko) — aucune régression sideload Chrome/Edge/Brave.
- Aucun secret ni artefact ne peut fuiter dans le zip de release (tout est hors extension/).

### Étape restant à l'utilisateur (action externe)
- Lancer `sh scripts/sign-firefox-extension.sh` avec AMO_JWT_ISSUER/AMO_JWT_SECRET (env ou .amo-credentials). La signature uploade vers Mozilla (compte externe).

### Garde-fous
- web-ext lint : 0 erreur, 0 warning (pré-vol de signature).
- manifest.json revalidé en JSON ; scripts/sign-firefox-extension.sh : sh -n OK, +x.
- node/npx vérifiés présents (v22).
---

[← retour à extension](index.md) · [voir log](../log.md)
