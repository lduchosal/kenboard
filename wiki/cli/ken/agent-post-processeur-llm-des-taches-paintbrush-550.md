---
id: 550
title: "AGENT / post-processeur LLM des tâches paintbrush"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-31T00:18:56
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: cli/ken
section_title: "ken task CLI"
---

# #550 — AGENT / post-processeur LLM des tâches paintbrush

Hors épic paintbrush #541. Reprend une tâche fraîchement poussée (avec attachement SVG + description brute) et reformule titre + description.

Design phase 1 : commande manuelle `ken polish <id>` qui prépare le contexte sur disque puis imprime un prompt agent. Pas d'appel LLM dans ken.

---

## Résolution

### Modifications
- src/dashboard/ken.py : nouvelle commande `polish` :
  - Fetch la tâche via /api/v1/tasks?project=<id> (réutilise le pattern de `show`).
  - Sauve la description dans `<tmp-dir>/kenboard-polish-<id>.md` (toujours, vide si pas de desc).
  - Sauve le SVG attachement dans `<tmp-dir>/kenboard-polish-<id>.svg` (uniquement si présent ; sinon "(aucun)" dans le prompt).
  - Imprime un prompt structuré : titre actuel, status, chemins disques, action attendue (1. lire 2. nouveau MODULE/Titre 3. réécrire desc actionnable 4. `ken update <id> --title ... --desc-file ...`).
  - Option `--tmp-dir` (défaut /tmp) pour tester sans polluer /tmp.
  - **Pas d'appel LLM** : ken reste sans dep réseau au-delà du stdlib.
- src/dashboard/agent_guide.md : section attachement étendue avec le shortcut `ken polish <id>`.
- tests/unit/test_ken.py : 2 tests :
  - tâche avec attachement → desc.md + svg + prompt avec les 2 chemins + "ken update X".
  - tâche sans attachement → desc.md seul, "(aucun)" dans le prompt, pas de fichier .svg créé.

### Comportement attendu en pratique

```
$ ken polish 579
# Polish task #579 — agent reformulation prompt

Titre actuel : 'KEN / Projets'
Status      : todo
Description sauvée dans : /tmp/kenboard-polish-579.md
  SVG attachement : /tmp/kenboard-polish-579.svg (ouvre-le pour voir...)

Action attendue (agent / LLM) :
  1. Lis la description (et le SVG si présent...).
  2. Produis un nouveau MODULE / Titre concis...
  3. Réécris la description...
  4. Applique :
       ken update 579 --title 'MODULE / ...' --desc-file /tmp/kenboard-polish-579.md
```

### Garde-fous
- mypy ken.py : clean.
- TestCliMutations : 108/108 passed (+2 nouveaux polish).
- Suite complète : 510 passed.
- ken --help liste `polish` parmi les commandes.

### Phase 2 envisageable
- `--auto` qui appelle directement un LLM (Claude / OpenAI) via stdlib urllib avec clé dans .env, et applique sans confirmation.
- Bouton UI sur le modal fullscreen qui appelle l'API kenboard pour déclencher le polish.

Mais phase 1 (manuelle) suffit pour démarrer.
---

[← retour à cli/ken](index.md) · [voir log](../../log/2026-05-31.md)
