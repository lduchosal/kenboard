---
id: 372
title: "QUALITY / Sonarcloud"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:30:07
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #372 — QUALITY / Sonarcloud

## Demande

https://sonarcloud.io/project/overview?id=lduchosal_kenboard — revue des issues, correction.

---

## Audit (Sonarcloud API, branche main, 2026-05-20)

### Compteurs globaux

| Métrique | Valeur |
|---|---|
| Bugs | **0** |
| Vulnerabilities | **0** |
| Code smells | **0** |
| Security hotspots (open) | **0** |
| Hotspots TO_REVIEW | **0** |
| Reliability rating | **A** (1.0) |
| Security rating | **A** (1.0) |
| Maintainability rating | **A** (1.0) |
| Duplicated lines density | **0.0%** |
| Coverage (global) | **87.3%** |
| Coverage on new code | **85.5%** |

### Détail des issues ouvertes

```
$ GET /issues/search?componentKeys=lduchosal_kenboard&resolved=false&ps=100
Total open issues: 0
```

Aucune issue de quelque sévérité que ce soit (BLOCKER / CRITICAL / MAJOR / MINOR / INFO).

## Résolution

**Aucun travail à faire** : le projet est dans un état Sonarcloud propre, hérité du travail récent (#268, #248, #257, #338 ont nettoyé les S1192 / S5793 / N+1 / coverage). Les passes \`pdm run check\` (composite Python + JS) gardent depuis la quality gate verte à chaque publish.

### Garde-fous structurels en place

- `publish.sh` exécute la quality gate Sonarcloud à chaque release (#346 a réglé le forwarding de `SONAR_TOKEN`).
- Quality profile config-as-code via `sonar-project.properties` (exclusions justifiées en commentaire).
- 395 tests Python + 61 tests JS + 52 tests e2e ; coverage 87.3% / 85.5% new code.

### Action

Task à fermer (ou \"done\") après review. Pas de commit nécessaire.
---

[← retour à quality](index.md) · [voir log](../log/2026-05-24.md)
