---
id: 514
title: "EXTENSION / capture textuelle structurée (remplace le screenshot PNG)"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-29T18:45:46
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: extension
section_title: "Browser extension"
---

# #514 — EXTENSION / capture textuelle structurée (remplace le screenshot PNG)

Remplacer le screenshot PNG base64 embarqué dans la description (popup.js) par une capture TEXTUELLE structurée de la page, en markdown : titre, URL, méta-description, plan des titres (h1-h3), et texte sélectionné par l'utilisateur. Objectif : la description MD de la tâche reflète la demande de l'utilisateur sans stocker de binaire en base (cf. #511). Décision produit : extraction structurée seule (pas d'ASCII-art, pas de pièces jointes).

---

## Résolution

### Modifications
- extension/popup.js — suppression du screenshot (chrome.tabs.captureVisibleTab + ![screenshot](data:...)). Nouvelle fonction extractPageInfo() injectée dans la page via chrome.scripting.executeScript : retourne titre, URL, méta-description, plan des titres (h1-h3, max 40), et la sélection courante. buildDescription() compose un bloc markdown : note utilisateur + Source + meta + **Outline** (liste imbriquée par niveau) + **Selection** (blockquote). Aucun binaire.
- extension/manifest.json — ajout de la permission "scripting" (requise par chrome.scripting.executeScript ; l'accès hôte vient déjà d'activeTab + <all_urls>).
- extension/popup.html — case "Include screenshot" → "Include page capture (outline + selection)" (id include-capture).
- extension/README.md — sections Use/Notes réécrites : capture markdown texte (pas d'image), conseils (sélectionner du texte avant d'ouvrir, décocher pour note seule), pages privilégiées non scriptables → fallback titre + URL.

### Comportements obtenus
- La tâche créée contient une description markdown texte reflétant la page (URL, plan, sélection) + la note de l'utilisateur. Plus aucun PNG/base64 → plus de dépassement de la colonne TEXT (cause de #511).
- Pages non scriptables (chrome://, about:, file://, store) : fallback gracieux titre + URL.

### Garde-fous
- node --check extension/popup.js : OK. extension/ hors périmètre Biome.
- web-ext lint : 0 erreur, 0 warning (manifest avec la nouvelle permission scripting).
- Logique buildDescription vérifiée en Node (avec page et sans page) — markdown bien formé.
- NON testé en navigateur ici : le chemin chrome.scripting.executeScript nécessite un vrai navigateur. À confirmer par un essai réel (recharger l'extension, capturer une page).
---

[← retour à extension](index.md) · [voir log](../log.md)
