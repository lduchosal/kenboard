---
id: 167
title: "AGENT / Rapeller à l'agent de mettre à jour la tâche"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:48
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: cli/ken
section_title: "ken task CLI"
---

# #167 — AGENT / Rapeller à l'agent de mettre à jour la tâche

Quand l'agent passe la tache de en cours à revue, il convient de lui rappeler les bonnes pratiques:
- Mettre à jour la tâche avec le résumé d'implémentation

---

## Résolution

Inversé les étapes 4 et 5 dans `CLAUDE.md` et `agent_guide.md` :
- Étape 4 : **mettre à jour la description** avec le bloc Résolution (Modifications, Comportements obtenus, Garde-fous)
- Étape 5 : **puis** `ken move <id> --to review`

Avant : l'agent faisait le move d'abord et oubliait parfois de mettre à jour la description.
---

[← retour à cli/ken](index.md) · [voir log](../../log.md)
