---
id: 472
title: "WIKI / groom"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-27T10:54:58
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/api
section_title: "REST API"
---

# #472 — WIKI / groom

ProgrammingError(1146, "Table 'dashboard.task_wiki_classifications' doesn't exist")
sur GET /api/v1/wiki/unclassified — error_id E-6a16aaa5-5227.

Le client n'avait pas de ARCHITECTURE.md correctement configuré.

---

## Résolution

### Approche

Améliorer le message côté CLI quand `ARCHITECTURE.md` ne donne pas de
sections — distinguer le fichier manquant vs présent-mais-vide, et
montrer dans les deux cas comment fixer (créer le fichier OU pointer
ken vers le bon chemin via `.ken`).

Le précédent commit (handler serveur 503 sur ProgrammingError 1146)
est retiré : ce n'était pas la bonne réponse à la cause racine.

### Modifications

- `src/dashboard/ken.py` :
  - Nouveau helper `_architecture_help(architecture)` qui renvoie un
    message multi-lignes :
    - **fichier manquant** : "ARCHITECTURE file not found: <path>",
      suivi de (a) un exemple complet de frontmatter YAML à copier,
      (b) commande pour configurer le chemin via `.ken` (et l'env
      `KEN_ARCHITECTURE` en alternative).
    - **fichier présent mais vide** : "<path> exists but declares no
      wiki sections", puis l'exemple de bloc `wiki.sections` à ajouter.
  - Les 4 sous-commandes (`wiki groom`, `sync`, `build`, `lint`)
    utilisent maintenant cet helper au lieu de leurs messages
    génériques précédents.
- `src/dashboard/routes/wiki.py` : retour à la version pré-#472
  (pas de handler 503 spécifique — la réponse était inadaptée
  selon le retour utilisateur).
- `tests/unit/test_ken.py::TestCliMutations` :
  - `groom` sans ARCHITECTURE.md → message contient "not found",
    le bloc YAML d'exemple (`wiki:`, `sections:`) et la ligne
    `architecture=`.
  - `sync` sans fichier → exit non-zéro + même message.
  - `sync` avec fichier sans `wiki.sections` → message distinct
    "exists but declares no wiki sections", toujours avec
    l'exemple YAML.
- `tests/unit/test_wiki_routes.py` : suppression de
  `TestMissingTableErrorIsFriendly` (cohérent avec le retrait du
  handler serveur).

### Comportements obtenus

- L'opérateur qui découvre le wiki et lance n'importe quelle
  commande `ken wiki *` sans ARCHITECTURE.md voit immédiatement
  les deux fixes possibles dans le message d'erreur.
- L'exemple YAML embarqué est directement copy-paste-able.
- La distinction "missing" vs "empty" évite l'effort inutile de
  chercher où ajouter un bloc dans un fichier qui n'existe pas.

### Garde-fous

- `pdm run check` : OK (474 tests, lint, typecheck, format, refurb).
- 3 nouveaux tests dans `test_ken.py`.
---

[← retour à backend/api](index.md) · [voir log](../../log.md)
