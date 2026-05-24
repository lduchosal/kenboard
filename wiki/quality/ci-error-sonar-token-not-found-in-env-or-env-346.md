---
id: 346
title: "CI / Error: SONAR_TOKEN not found in env or .env"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:30:01
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #346 — CI / Error: SONAR_TOKEN not found in env or .env

## Demande

```
═══════════════════════════════════════════════════════════════
  23/28 Sonarcloud Quality Gate
═══════════════════════════════════════════════════════════════

Error: SONAR_TOKEN not found in env or .env
✗ Sonarcloud quality gate FAILED — aborting publish
Error: Process completed with exit code 1.
```

*Note de la review : l'URL initialement collée pointait vers le repo `jeff`. Le run réel concerné est celui du repo `kenboard` — corrigé ci-dessous.*

---

## Diagnostic

Le secret `SONAR_TOKEN` était bien configuré dans **Settings → Secrets and variables → Actions** du repo `kenboard`. Pourtant la step *Publish* (qui invoque `publish.sh`) échouait sur la quality gate parce que GitHub Actions **n'expose pas automatiquement** les secrets aux processus de step — ils doivent être mappés explicitement sous le bloc `env:` de la step.

Le step *Publish* dans `.github/workflows/publish.yml` mappait `PDM_PUBLISH_USERNAME` et `PDM_PUBLISH_PASSWORD` pour PyPI mais pas `SONAR_TOKEN`. Conséquence : `scripts/sonar_gate.py` lit `os.environ.get(\"SONAR_TOKEN\", \"\")` → chaîne vide → hard fail.

L'autre workflow (`python-package.yml`, scan SonarCloud) mappait déjà correctement `SONAR_TOKEN: \${{ secrets.SONAR_TOKEN }}` sur sa step *SonarCloud Scan* — d'où la confusion.

## Résolution

### Modifications

- `.github/workflows/publish.yml` : ajouter `SONAR_TOKEN: \${{ secrets.SONAR_TOKEN }}` au bloc `env:` de la step *Publish*. Commentaire explicatif pour qu'un futur lecteur comprenne pourquoi.

### Comportement obtenu

Le prochain workflow `publish.yml` (cron du lundi 9h UTC ou `workflow_dispatch`) pourra lire `SONAR_TOKEN` depuis l'environnement, `sonar_gate.py` poll Sonar Cloud normalement, la gate s'évalue.

### Garde-fous

- Aucune modif Python — `pdm run check` toujours 395 passed.
- Le secret reste géré côté repo settings, pas dans le code — pas de regression sécurité.

## Note pour les forks / projets dérivés

Tout repo qui réutilise ce `publish.yml` (fork de kenboard, `jeff`, autres sibling projects) doit également avoir :
1. Le secret `SONAR_TOKEN` configuré dans repo settings.
2. Le mapping `SONAR_TOKEN: \${{ secrets.SONAR_TOKEN }}` dans la step *Publish* du workflow.

Sans le mapping (point 2), le secret est invisible à `publish.sh` même s'il existe dans les settings.
---

[← retour à quality](index.md) · [voir log](../log.md)
