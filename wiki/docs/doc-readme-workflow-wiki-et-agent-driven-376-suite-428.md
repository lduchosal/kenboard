---
id: 428
title: "DOC / README — workflow wiki et agent-driven (#376 suite)"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-25T13:53:52
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: docs
section_title: "Documentation"
---

# #428 — DOC / README — workflow wiki et agent-driven (#376 suite)

Le README actuel ne mentionne pas le workflow wiki agent-driven (#376a–f). Ajouter une section expliquant le cycle complet.

## À couvrir

1. **Pour l'humain** : démarrer un projet sur kenboard, créer une API key, installer `ken`, bootstrap `.ken` (`ken init <project>`).
2. **Pour l'agent (Claude / GPT / …)** : boucle de travail `ken list → move doing → implement → update --desc → move review → groom`.
3. **Wiki feature (#376)** : groom / sync / build / lint.

## Hors scope

- Pas de réorganisation des sections existantes du README
- Garder le ton concis (le README est déjà long)

---

## Résolution

### Modifications

- `README.md` :
  - Ajout de `ken wiki groom <id> <section>` dans le bloc "Daily workflow"
  - Mise à jour du cycle complet : `todo → doing → review → groom → done`
    + mention du reminder émis par le CLI sur `move/update --to review`
  - Nouvelle section "Wiki — exporting the board as a structured doc tree (#376)"
    couvrant les 4 commandes (groom / sync / build / lint), la référence
    au LLM Wiki de Karpathy, le rôle de `ARCHITECTURE.md`, le pattern
    "serveur unaware", la segmentation En cours / Archivé, la reprise
    du template fullscreen pour les pages détail, et le hook CI via
    `lint --strict`. Lien vers `/wiki` (snapshot committed).

### Comportements obtenus

- Un humain qui découvre kenboard sur GitHub voit immédiatement que
  le wiki est généré depuis le board (pas un système séparé à
  maintenir), et trouve la chaîne de commandes pour l'expérimenter.
- Un agent qui lit le README a une cheat-sheet complète du loop
  (workflow + grooming) en un coup d'œil.

### Garde-fous

- `pdm run check` : OK (466 tests, lint, typecheck, format).
- README rendu vérifié visuellement (markdown valide).
---

[← retour à docs](index.md) · [voir log](../log/2026-05-25.md)
