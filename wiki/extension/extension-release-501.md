---
id: 501
title: "EXTENSION / Release"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-29T08:50:08
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: extension
section_title: "Browser extension"
---

# #501 — EXTENSION / Release

L'extension n'est pas présente dans le release 0.1.112
https://github.com/lduchosal/kenboard/releases/tag/kenboard-0.1.112

---

## Résolution

### Diagnostic
Bilan des releases : 0.1.110, 0.1.111, 0.1.113 ont bien release + zip extension ; seul 0.1.112 n'a AUCUNE release GitHub (le tag existe, pas l'objet release). Cause racine : dans publish.sh le step était `gh release create ... || echo WARN` — best-effort, qui avalait silencieusement tout échec (hiccup réseau/transient) et laissait un tag sans release ni extension. Risque latent supplémentaire : le workflow CI publish.yml n'exposait pas de GH_TOKEN au step Publish, donc tout run planifié/dispatch ne pouvait de toute façon pas créer de release (gh non authentifié).

### Modifications
- publish.sh — step "Publishing GitHub Release" rendu idempotent et bruyant : si une release existe déjà pour le tag → `gh release upload --clobber` (attache quand même l'extension) ; sinon `gh release create --generate-notes` ; en cas d'échec, erreur rouge + commande de récupération exacte (non-fatal car PyPI a déjà shippé — aborter induirait en erreur).
- .github/workflows/publish.yml — ajout de `GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}` au step Publish (le token par défaut a contents:write via les permissions du workflow), pour que les publishs CI/planifiés puissent créer la release.

### Décision (validée avec l'utilisateur)
Fix forward uniquement : pas de rétro-création de la release 0.1.112. 0.1.113 fournit déjà l'extension aux utilisateurs et reste "Latest" ; backfiller 0.1.112 était marginal. (Le zip 0.1.112 avait été préparé depuis le tag mais non publié.)

### Comportements obtenus
- Les prochains publishs (local ET CI) attachent l'extension de façon fiable ; un échec n'est plus silencieux et donne la commande de récupération.
- Idempotent : si la release a déjà été créée (ex. par le workflow sur push de tag), l'extension est tout de même attachée via --clobber.

### Garde-fous
- `sh -n publish.sh` OK ; publish.yml validé en YAML (yaml.safe_load).
---

[← retour à extension](index.md) · [voir log](../log.md)
