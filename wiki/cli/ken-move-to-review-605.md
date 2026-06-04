---
id: 605
title: "KEN / move to review"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-31T21:04:30
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: cli
section_title: "Command-line interface"
---

# #605 — KEN / move to review

Lors du ken move --to review un message à destination de l'agent LLM doit lui rappeller de mettre à jour la tâche ken avec les détails de l'implémentation pour un bon suivi. Les données du ticket initiale doivent être conservées au mieux et une section peut être ajoutée avec les détails de la réalisation

---

## Résolution

### Modifications
- src/dashboard/ken.py — ajout de `_review_update_reminder(task_id)`, déclenché depuis `move --to review` (l.891) et `update --status review` (l.781). Imprime sur stderr (n'altère pas `--json`), avant le rappel wiki_groom existant.
- tests/unit/test_ken.py — nouveaux tests test_move_to_review_prints_update_reminder et test_update_status_review_prints_update_reminder ; assertion supplémentaire sur test_move pour vérifier qu'aucun rappel "Résolution" ne fuit sur les transitions non-review.

### Comportements obtenus
- `ken move <id> --to review` et `ken update <id> --status review` impriment deux rappels stderr : (1) mettre à jour la description en préservant l'original + section ## Résolution avec Modifications/Comportements/Garde-fous ; (2) classer pour le wiki (rappel existant #376).
- `ken move <id> --to doing|todo|done` n'affiche aucun rappel — assertion testée.

### Garde-fous
- pdm run pytest tests/unit/test_ken.py -k 'move or update_status_review or wiki_groom' → 18 passed
- pdm run lint → All checks passed
- pdm run typecheck → Success: no issues found in 30 source files
---

[← retour à cli](index.md) · [voir log](../log/2026-05-31.md)
