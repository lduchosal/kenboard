---
id: 1238
title: "QUALITY / Ajoute deptry et pip-audit au publish.sh"
status: done
who: "Claude"
due_date: 
updated_at: 2026-11-26T15:28:25
classified_at: 2026-11-25T23:17:44
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #1238 — QUALITY / Ajoute deptry et pip-audit au publish.sh

**TL;DR** — Le gate Python n'avait ni contrôle des dépendances déclarées/importées ni audit de vulnérabilités (pendant de `npm audit`) → deptry et pip-audit ajoutés à `publish.sh` (steps 6-7, juste après `pdm update`) ; les 2 imports transitifs que deptry a révélés (`werkzeug`, `certifi`) sont désormais déclarés.

Le gate qualité de `publish.sh` couvre le JS côté dépendances (`npm audit`, step 17) mais rien d'équivalent côté Python : aucune vérification des dépendances déclarées vs importées, aucun audit de vulnérabilités des paquets PyPI.

## À faire

- **deptry** — détecte les dépendances manquantes (importées mais non déclarées), inutilisées (déclarées mais jamais importées), transitives utilisées directement, et mal rangées (dev vs runtime) dans `pyproject.toml`.
- **pip-audit** — audit des vulnérabilités connues (PyPA advisory DB / OSV) sur l'environnement résolu (`pdm.lock`).

## Pistes

- Ajouter les deux outils aux dev-deps (`>=` sans borne haute, cf. convention ratchet), scripts PDM `deptry` / `pip-audit` (et/ou `py-audit`), intégrés au composite `pdm run check` si pertinent.
- Deux `print_step` dans `publish.sh`, à côté de `npm audit` (après `pdm update`, avant le lint) ; message d'échec actionnable comme pour `js-audit`.
- Recalculer les compteurs `STEPS` (24/26/37/40 → +2) et le commentaire qui les détaille (ken #1009).
- Config deptry dans `[tool.deptry]` : mapping paquet→module (ex. `PyMySQL`→`pymysql`, extras `[prod]` type gunicorn non importés), exclusions `tests/`, `vulture_whitelist.py`, ext VS Code.
- pip-audit : pas d'ignore silencieux — toute exception `--ignore-vuln` justifiée en commentaire avec l'ID ken.
- Sortie propre : zéro warning/bruit dans le log publish.sh.
- Ajouter au workflow CI si le gate y tourne aussi.

## Résolution

### Modifications

- `pyproject.toml`
  - dev-deps `deptry>=0.25.1`, `pip-audit>=2.10.1` (plancher, sans borne haute — ratchet) ; commentaires existants préservés (`pdm add` les avait supprimés).
  - runtime : `werkzeug>=3.1` (ProxyFix importé dans `app.py`) et `certifi>=2024.2.2` (CA bundle de `ken/http.py`) déclarés — deptry DEP003, ils ne tenaient que par les pins de flask / requests. Commentaire ajouté sur `requests` (jamais importé, besoin runtime d'`authlib.integrations.flask_client`, #126).
  - `[tool.deptry]` : scan de `src/` seul (contrat runtime du paquet publié), `known_first_party = ["dashboard"]`, `per_rule_ignores.DEP002` commentés un par un : `yoyo-migrations` (binaire `yoyo` appelé par `kenboard migrate`), `requests` (#126), `pip-system-certs` (extra `[oidc]`, patch via `.pth`, #344) ; `package_module_name_map` pour `pip-system-certs` (pas installé en dev → supprime le message « Assuming… »).
  - scripts PDM `deptry` (`deptry src`) et `py-audit` (`pip-audit --skip-editable --progress-spinner off`) ; `deptry` ajouté au composite `check` (offline, 2 s). `py-audit` en est exclu : réseau (même traitement que `js-audit`).
- `publish.sh` — 2 `print_step` après `pdm update --update-all` (venv fraîchement résolu) : « Dependency Hygiene (deptry) » et « Python Security Audit (pip-audit) », message d'échec actionnable ; compteurs `STEPS` 24/26/37/40 → 26/28/39/42 et commentaire (ken #1009) mis à jour — 42 `print_step` = mode release non-CI.
- `src/dashboard/ken/http.py` — docstring `_ssl_context` : certifi n'est plus « transitive via requests » mais déclaré.
- `CLAUDE.md` — `deptry` / `py-audit` dans *Common commands*, composite `check` à jour.

### Comportements obtenus

- deptry : `Success! No dependency issues found.` (5 issues avant : 3 DEP002 légitimes → ignorés commentés, 2 DEP003 → déclarés).
- pip-audit : audite le venv entier (155 paquets runtime + dev, kenboard éditable exclu) → `No known vulnerabilities found`. Aucun `--ignore-vuln`.
- CI : `publish.yml` lance `publish.sh --ci`, les deux gates y tournent sans modification du workflow.

### Garde-fous

- `sh publish.sh --quality` : **28/28 vert**, aucune ligne ⚠ — mypy 0, interrogate 100 %, ruff/flake8/refurb/vulture clean, npm audit 0, vitest 82, VS Code 17, pytest 825, E2E 52, metrics gate PASS.
- Hors périmètre, préexistant : la step `npm ci` résume sur `npm notice` (avis « npm 10.9.9 → 12.2.3 » dans le log).
---

[← retour à quality](index.md) · [voir log](../log/2026-11-25.md)
