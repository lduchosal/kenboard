---
id: 163
title: "AGENT / Json semble un problème"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:44
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: cli/ken
section_title: "ken task CLI"
---

# #163 — AGENT / Json semble un problème

Claude invoque systematiquement le ken avec un import python et un print title, perdant tout l'interet du json.

Bash(ken show 158 --json 2>&1 | python3 -c "import
      sys,json; d=json.load(sys.stdin);
      print(d['title']); print('status:',
      d['status']); print('---'); print(d.get('des…)

On se pose la question sur le --json dans le onboarding et les bonnes pratique a du sens. Analyser et donner une réponse

---

## Résolution

### Analyse

Le problème vient du guide agent (`agent_guide.md`) et du `CLAUDE.md` qui recommandaient `--json` sur toutes les commandes de lecture (`ken list`, `ken show`). Claude interprétait ça comme "toujours utiliser --json", puis pipait la sortie dans `python3 -c "import sys,json; ..."` pour extraire les champs — verbeux, lent, et inutile puisqu'un LLM lit du texte nativement.

Or `ken list` produit un tableau aligné et `ken show` un format clé-valeur, tous deux directement lisibles sans post-traitement.

### Modifications

- `src/dashboard/agent_guide.md` — retiré `--json` des exemples de lecture (list, show), reformulé la section "Filters and output" pour recommander le format texte par défaut
- `CLAUDE.md` — même alignement : `ken list` et `ken show` sans `--json`, guidance mise à jour

### Comportements obtenus

- Les agents utiliseront le format texte par défaut pour les commandes de lecture
- `--json` reste disponible et recommandé uniquement pour `ken add` (capturer l'ID créé)
- Plus de pipes python/jq inutiles

### Garde-fous

- `pdm run lint` → All checks passed
- `pdm run typecheck` → no issues found in 24 source files
- `pdm run test-quick` → 269 passed
---

[← retour à cli/ken](index.md) · [voir log](../../log/2026-05-24.md)
