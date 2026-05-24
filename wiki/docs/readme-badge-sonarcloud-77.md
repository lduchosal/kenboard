---
id: 77
title: "README / badge sonarcloud"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:20
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: docs
section_title: "Documentation"
---

# #77 — README / badge sonarcloud

Ajouter les badges sonarcloud dans le README.md.

## Fix

Ajout d'une seconde ligne de badges dédiée à SonarCloud, juste après les badges existants. 8 badges, tous pointant vers `https://sonarcloud.io/summary/new_code?id=lduchosal_kenboard`:

- Quality Gate Status (alert_status) — overall pass/fail
- Maintainability Rating (sqale_rating)
- Reliability Rating (reliability_rating)
- Security Rating (security_rating)
- Bugs (bugs)
- Vulnerabilities (vulnerabilities)
- Code Smells (code_smells)
- Technical Debt (sqale_index)

Coverage est volontairement laissé à codecov (#76) pour ne pas dupliquer.
---

[← retour à docs](index.md) · [voir log](../log.md)
