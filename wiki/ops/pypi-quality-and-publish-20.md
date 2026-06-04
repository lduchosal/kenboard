---
id: 20
title: "PYPI / Quality and publish"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:12
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: ops
section_title: "Ops & deployment"
---

# #20 — PYPI / Quality and publish

Execute la qualité, résoud les problèmes et publie le package sur pypi.

## Quality

Déjà au vert avant lancement (fait pendant le fix #19) : ruff, mypy, black, isort, docformatter, flake8, vulture, refurb, interrogate 100%, 64 unit + 29 e2e = 93 tests verts. Aucun fix nécessaire dans publish.sh --quality.

## sh publish.sh

24/24 étapes OK.

- Version : 0.1.13 → **0.1.14**
- PyPI : https://pypi.org/project/kenboard/0.1.14/ — sdist + wheel uploadés
- Git : commit `d7d8937` `chore: release version 0.1.14` (4 fichiers, +181/-17), tag `kenboard-0.1.14`, pushé sur `main`

## Contenu de la release 0.1.14

- Fix #19 : Firefox form history autofill faisait croire que Q était écrasé après création d'un nouveau user. Ajout de `autocomplete="off"` sur les inputs name/color, `autocomplete="new-password"` sur les passwords. Bouton Créer en `btn-save` (bleu) pour le distinguer visuellement de Enregistrer/Supprimer.
- 3 nouveaux tests e2e dont un dédié Firefox (`test_firefox_create_user_no_autofill_leak`) qui valide le fix bidirectionnellement.
---

[← retour à ops](index.md) · [voir log](../log/2026-05-24.md)
