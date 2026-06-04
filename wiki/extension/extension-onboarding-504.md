---
id: 504
title: "EXTENSION / Onboarding"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-29T08:13:06
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: extension
section_title: "Browser extension"
---

# #504 — EXTENSION / Onboarding

Dans la fenêtre de configuration, mettre un champ URL où l'on peut coller le "Copy onboarding link" provenant du kenboard.

---

## Résolution

### Modifications
- extension/options.html — nouveau champ "Onboarding link" (type=url) en haut du formulaire, au-dessus de Base URL.
- extension/options.js — fonction applyOnboardLink() branchée sur l'événement `input` du champ. Elle parse `<origin>/onboard/cat/<cat>/project/<project>?token=<key>` (le format généré par category.html → copyOnboardLink) et remplit baseUrl (url.origin), projectId (segment de path) et apiToken (query `token`).
- extension/README.md — section First-run : ligne "Onboarding link" présentée comme le chemin le plus rapide.

### Comportements obtenus
- Coller le lien "Copy onboard link" remplit automatiquement Base URL + Project ID + API token ; l'utilisateur n'a plus qu'à vérifier et Save.
- Lien sans token : remplit Base URL + Project ID et signale qu'il faut ajouter le token manuellement.
- URL invalide ou non-onboard : message d'erreur, aucun champ écrasé silencieusement à tort (la regex exige …/onboard/cat/…/project/…).
- Le lien collé n'est pas persisté (seuls baseUrl/apiToken/projectId/defaultWho le sont, comportement save() inchangé).

### Garde-fous
- Logique de parsing testée en Node sur 4 cas (lien complet, trailing slash + localhost:port, sans token, non-onboard) — tous OK.
- extension/ est hors périmètre Biome (biome.json n'inclut que src/dashboard/static/js/**), style aligné sur l'existant (double quotes, 2 espaces, point-virgules, trailing commas).
- Aucun changement serveur : réutilise l'endpoint /onboard et l'API existante.
---

[← retour à extension](index.md) · [voir log](../log/2026-05-29.md)
