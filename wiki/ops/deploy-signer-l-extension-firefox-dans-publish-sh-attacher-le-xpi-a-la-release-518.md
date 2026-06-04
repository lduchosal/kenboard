---
id: 518
title: "DEPLOY / signer l'extension Firefox dans publish.sh + attacher le .xpi à la release"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-29T22:31:33
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: ops
section_title: "Ops & deployment"
---

# #518 — DEPLOY / signer l'extension Firefox dans publish.sh + attacher le .xpi à la release

Intégrer 'sh scripts/sign-firefox-extension.sh' dans publish.sh : après le bump de version (AMO exige une version unique), gated sur la présence de credentials AMO (.amo-credentials ou env), best-effort (ne bloque jamais le publish), et attacher le .xpi signé à la release GitHub à côté du zip. Skip propre si pas de creds (ex. CI).

---

## Résolution

### Modifications
- publish.sh — nouveau bloc après le bloc "GitHub Release" (donc après le bump de version → manifest à jour, et après la création/maj de la release) :
  - gardé par `[ -d extension ] && { [ -f .amo-credentials ] || (AMO_JWT_ISSUER && AMO_JWT_SECRET) }` → skip propre ("Skipping Firefox signing (no AMO credentials)") sinon (ex. CI sans secret).
  - lance `sh scripts/sign-firefox-extension.sh` ; en cas de succès, retrouve le .xpi signé via `ls -t web-ext-artifacts/*-${VERSION}.xpi` et l'attache à la release avec `gh release upload --clobber`.
  - best-effort : aucune erreur n'avorte le publish (PyPI + zip déjà shippés) ; pas de print_step (le bloc est conditionnel) pour ne pas fausser le compteur d'étapes.
- extension/README.md — section "Firefox (persistent)" : note que les releases attachent un .xpi signé (suffixe -<version>.xpi) quand l'éditeur a configuré les creds AMO → chemin le plus simple = télécharger depuis les releases.

### Comportements obtenus
- Un publish avec creds AMO signe l'extension à la version fraîchement bumpée et publie le .xpi sur la release, à côté du zip.
- Un publish sans creds (CI, ou local sans .amo-credentials) saute la signature proprement, sans bloquer.

### Garde-fous
- sh -n publish.sh : OK.
- NON exécuté de bout en bout ici (nécessiterait un vrai publish + upload AMO). Le glob *-${VERSION}.xpi correspond au nommage web-ext (GUID-addon + version). Logique gated/best-effort relue.
---

[← retour à ops](index.md) · [voir log](../log/2026-05-29.md)
