---
id: 376
title: "Export / wiki"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:30:07
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: wiki
section_title: "Wiki (#376)"
---

# #376 — Export / wiki

## Demande initiale

Exporter le contenu kenboard en arbre MD structuré (basé sur ARCHITECTURE.md), pas en plat. Rendre HTML pour utilisateur final.

## Référence : LLM Wiki pattern (Karpathy)

https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f

3 couches : raw sources (tâches DB) → wiki MD curated → schéma (ARCHITECTURE.md). Opérations : ingest / query / lint. Fichiers index.md (catalogue) + log.md (append-only). Insight clé : *\"the tedious part of maintaining a knowledge base is not the reading or thinking — it's the bookkeeping\"* — le LLM gère le bookkeeping, l'humain curate.

## Décisions verrouillées

1. **Format ARCHITECTURE** : frontmatter YAML dans `ARCHITECTURE.md`.
2. **Classify** : **agent-driven via CLI**. `ken wiki groom` (no args) → liste tâches non classifiées + sections dispo. L'agent appelle `ken wiki groom <id> <section>` une fois par tâche. `ken wiki groom --help` explique le concept (lien gist) à l'agent. Pas d'API LLM dans le code de ken.
3. **Wiki path** : `wiki/` gitignored par défaut. Flag `--output doc/wiki/` pour committer.
4. **HTML render** : inline CSS minimal style burndown — zéro dep Python ni JS.
5. **Échelle** : règles simples + agent. ~400 tâches → quelques secondes. Pas de pagination.
6. **`log.md` append-only** : un append par run de sync, format parsable.
7. **Profondeur sections** : 2 niveaux max (section/sub).
8. **Multi-classes** : une section physique + tags YAML pour cross-ref.
9. **Storage classifications** : **table dédiée** `task_wiki_classifications (task_id, section_path, classified_at, classified_by)`. Sépare les concerns, garde l'historique des re-grooms, traçable.

## Découpage en sous-tâches (1 release par chunk)

- **A. WIKI / Schema + storage** — migration table `task_wiki_classifications`, parser frontmatter `ARCHITECTURE.md`, aiosql queries, tests unit.
- **B. WIKI / ken wiki groom** — commandes `groom`, `groom <id> <section>`, `groom --show`, `groom --clear`, `groom --help` avec concept Karpathy + lien gist.
- **C. WIKI / ken wiki sync** — walk classifications + tasks → écrit arbre MD + `index.md` par section + `WIKI.md` racine, append `log.md`.
- **D. WIKI / ken wiki build** — MD → HTML inline-CSS, sidebar nav, `--serve` via http.server stdlib.
- **E. WIKI / ken wiki lint** — orphelins, sections vides, classifications obsolètes.

Sous-tâche créée séparément sur le board pour chaque chunk afin de garder l'audit trail propre. Ce ticket reste l'umbrella et passera en review une fois A→E shipped.
---

[← retour à wiki](index.md) · [voir log](../log/2026-05-24.md)
