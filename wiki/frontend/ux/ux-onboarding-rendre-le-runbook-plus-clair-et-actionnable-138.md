---
id: 138
title: "UX / Onboarding / Rendre le runbook plus clair et actionnable"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:40
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/ux
section_title: "UX / interactions"
---

# #138 — UX / Onboarding / Rendre le runbook plus clair et actionnable

Le runbook onboarding actuel (renvoyé par le 401 ou curl) n'est pas assez clair. Un agent ou un humain qui le lit doit comprendre **immédiatement** les 3 étapes sans ambiguïté :

1. `pip install kenboard`
2. `ken init <project_id>` (avec les IDs déjà interpolés)
3. L'utilisateur humain fournira l'API key à coller dans le fichier `.ken`

## Problèmes actuels

- Le texte mentionne `cat_id` et `project_id` séparément, ce qui prête à confusion. L'agent a besoin du `project_id` (qui est dans le fragment `#` de l'URL) mais le serveur ne le voit pas — le runbook demande à l'agent de le "copier depuis l'URL originale" ce qui est vague.
- Les instructions pour créer le fichier `.ken` manuellement sont trop détaillées pour un premier contact. L'agent devrait juste voir : `pip install kenboard`, `ken init`, "demande l'API key à ton utilisateur".
- Le ton est technique ("HTTP clients drop the URL fragment") alors que l'audience est un agent IA qui a besoin d'instructions copy-paste.

## Proposition

Réécrire le runbook en 3 blocs clairs :

```
KENBOARD — Pour accéder à ce board, 3 étapes :

1. pip install kenboard

2. ken init <project_id>
   (remplacer <project_id> par l'UUID après # dans l'URL que l'utilisateur vous a donnée)

3. Demander à l'utilisateur de générer une API key sur /admin/keys
   et de la coller dans le fichier .ken généré par ken init
   (ligne api_token=)

Ensuite :
   ken list --status todo --json
   ken show <id> --json
   ken add "Titre" --desc "..." --who Claude --status todo
```

## Acceptation

- Un agent IA (Claude, GPT, etc.) qui lit le runbook comprend et exécute les 3 étapes sans aide humaine supplémentaire (sauf pour l'API key).
- Un humain qui fait `curl` sur l'URL comprend aussi.
---

[← retour à frontend/ux](index.md) · [voir log](../../log.md)
