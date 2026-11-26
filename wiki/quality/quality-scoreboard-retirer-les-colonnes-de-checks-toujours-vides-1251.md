---
id: 1251
title: "QUALITY / Scoreboard : retirer les colonnes de checks toujours vides"
status: done
who: "Claude"
due_date: 
updated_at: 2026-11-27T00:19:32
classified_at: 2026-11-26T16:57:41
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #1251 — QUALITY / Scoreboard : retirer les colonnes de checks toujours vides

**TL;DR** — La prémisse du ticket était fausse : les 4 checks « toujours vides » sont remplis pour les projets qui publient leur propre scorecard (urllib3, idna, charset-normalizer, pip-system-certs). Les retirer aurait détruit des données → colonnes gardées et documentées. Le board distingue maintenant la copie deps.dev d'un scorecard réellement ancien, et liste automatiquement les paquets sans aucun scorecard (« Angles morts »).

Suite de #1242. L'API OpenSSF (`api.securityscorecards.dev/projects/…`) ne renvoie plus que 14 checks : `Vulnerabilities`, `Contributors`, `CI-Tests` et `Dependency-Update-Tool` sont absents pour tous les paquets → 4 colonnes toujours vides dans `doc/dep-scorecard.{csv,md}`, qui suggèrent à tort une donnée manquante par paquet.

## À faire

- Retirer ces 4 checks de `CHECKS` dans `scripts/dep_scorecard.py` (ou ne garder que les colonnes non vides sur l'ensemble du snapshot) ; adapter la lecture de l'historique CSV existant (colonnes en trop ignorées), sans réécrire les snapshots committés.
- Mentionner dans `doc/code-quality.md` (§ chaîne d'approvisionnement) que `Vulnerabilities` est couvert par pip-audit, pas par le scorecard.
- Signaler distinctement dans le board les lignes « (ancien) » issues du fallback deps.dev (wrapt, cffi, markdown, pip) vs scorecard OpenSSF réellement vieux (pip-system-certs 2023-11-20, gitlab).
- Mentionner les angles morts connus (paquets sans scorecard mais critiques : `authlib`, `joserfc` — pile OIDC ; `yoyo-migrations` traité par une tâche dédiée).


## Résolution

### Correction de la prémisse

Dans le snapshot courant, `Vulnerabilities`, `CI-Tests`, `Contributors` et `Dependency-Update-Tool` sont remplis pour 3 à 4 paquets : charset-normalizer, idna et urllib3 (scorecards du 24 au 26 novembre 2026), ainsi que pip-system-certs (2023). Ces projets publient leur propre scorecard complet via `scorecard-action`. Le scan hebdomadaire d'OpenSSF, lui, saute ces 4 checks, coûteux en appels d'API. Vide veut donc dire « non mesuré », pas « absent de l'API ». Retirer ces colonnes de `CHECKS` aurait perdu ces mesures et cassé la continuité du CSV. Elles sont gardées.

### Modifications

- `scripts/dep_scorecard.py` :
  - docstring : explique les 4 checks partiels et rappelle que les vulnérabilités connues relèvent de pip-audit ;
  - `_date_cell()` : la colonne *Scorecard du* affiche `(deps.dev)` quand la donnée vient du repli deps.dev, `(ancien)` au-delà de 90 jours, et les deux si les deux s'appliquent. Avant, markdown, pymysql et pip-system-certs portaient tous le même « (ancien »), alors que les deux premiers sont la copie deps.dev et le troisième un scan OpenSSF arrêté en 2023 ;
  - `_blind_spots()` : nouvelle section « Angles morts » à la fin du board, qui liste les paquets sans aucun scorecard, avec leur repo et leur attestation PyPI. La section disparaît s'il n'y en a pas.
- `doc/code-quality.md` § Scorecard : comment lire le board (marqueurs de date, angles morts, les 4 checks partiels).
- `doc/dep-scorecard.md` : régénéré par `pdm run dep-scorecard`. Il montre `2026-08-24 (deps.dev, ancien)` pour markdown et pymysql, `2023-11-20 (ancien)` pour pip-system-certs, et les angles morts authlib, blinker, joserfc et typing-inspection.

### Comportements obtenus

- La pile OIDC (authlib, joserfc) figure désormais de façon visible et automatique dans les angles morts du board, sans dépendre d'une note manuelle.
- Le CSV d'historique garde son schéma : les snapshots committés ne sont pas réécrits.

### Garde-fous

- `tests/unit/test_dep_gates.py` : 3 nouveaux tests (marqueurs deps.dev et ancien séparés ou combinés, contenu des angles morts, absence de la section sans angle mort). 22 tests passent.
- `pdm run check` : exit 0, 880 tests. ruff et mypy passent sur `scripts/dep_scorecard.py`.
- `pdm run dep-scorecard` : 0 divergence.
---

[← retour à quality](index.md) · [voir log](../log/2026-11-26.md)
