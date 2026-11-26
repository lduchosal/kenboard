---
id: 1241
title: "QUALITY / GuardDog bloquant au publish.sh (paquets PyPI malveillants)"
status: done
who: "Claude"
due_date: 
updated_at: 2026-11-26T15:28:26
classified_at: 2026-11-25T23:49:40
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #1241 — QUALITY / GuardDog bloquant au publish.sh (paquets PyPI malveillants)

**TL;DR** — Rien dans le gate ne détectait un paquet PyPI *malveillant* (pip-audit ne voit que les failles publiées) → étape bloquante « Malicious Package Scan (guarddog) » dans `publish.sh` sur la fermeture runtime de `kenboard[prod,oidc]` (48 paquets), GuardDog en venv isolé avec cache par version (~4 min à froid, 1,5 s à chaud), faux positifs en allowlist (paquet, règle, fichiers) motivée après lecture du code.

Suite de #1238 (deptry + pip-audit). pip-audit ne voit que les vulnérabilités **déjà publiées** ; rien dans le gate ne détecte un paquet **malveillant** (typosquatting, release compromise, compte mainteneur repris). GuardDog (Datadog, open source) analyse le code et les métadonnées des paquets PyPI avec des heuristiques semgrep + yara : exfiltration, code obfusqué, `exec` de base64, scripts d'install suspects, domaine mail du mainteneur expiré, paquet fraîchement publié, etc.

## À faire

- Étape **bloquante** dans `publish.sh`, à côté de deptry / pip-audit (après `pdm update --update-all`, venv fraîchement résolu) : toute alerte GuardDog stoppe le build.
- Script PDM dédié (ex. `pdm run py-malware`) ; hors composite `check` (réseau + lent), comme `js-audit` / `py-audit`.
- Compteurs `STEPS` +1 et commentaire associé (ken #1009) ; `CLAUDE.md` § Common commands.

## Points à trancher pendant l'implémentation

- **Périmètre** : dépendances runtime + extras `[prod,oidc]` (ce qui part sur les hôtes FreeBSD) via `pdm export --prod --without-hashes` → `guarddog pypi verify <req.txt>`. Mesurer le temps ; étendre aux dev-deps (≈155 paquets, chaîne d'outillage = surface d'attaque réelle aussi) si le coût reste raisonnable, sinon documenter le choix.
- **Installation** : guarddog tire semgrep (lourd, binaire). Évaluer dev-dep vs exécution isolée (`uvx` / `pipx run`) pour ne pas polluer le résolveur ni casser `pdm update --update-all`. Jamais sur les hôtes de prod (pas de compilateur, cf. #499) — laptop + CI seulement.
- **Faux positifs** : exclusions ciblées (`--exclude-rules` par règle, ou par paquet) dans la config, chacune commentée avec sa justification et l'ID ken. Pas d'ignore global.
- **Sortie propre** : une ligne de résumé, zéro warning/bruit dans le log publish.sh ; en échec, le paquet + la règle + le fichier concerné doivent être lisibles dans le tail du log.
- CI : `publish.yml` lance `publish.sh --ci` → vérifier que l'étape tourne sur le runner (dépendances système de semgrep, durée).

## Résolution

### Modifications

- `scripts/runtime_deps.py` (nouveau, partagé avec #1242) — fermeture runtime : `pdm export --prod` (lock fraîchement résolu) + extras `[project.optional-dependencies]` (absents du lock : `oidc` clashe avec le truststore de pdm) et leurs dépendances inconditionnelles, récursivement (version de la venv, sinon dernière release PyPI). Révèle que `[oidc]` tire `pip` (via pip-system-certs). TLS sur certifi (le Python python.org macOS n'a pas de bundle CA).
- `scripts/guarddog_gate.py` (nouveau) —
  - venv isolé `.cache/guarddog/venv`, `pip install --upgrade guarddog` à chaque run (pas de pin). Pas en dev-dep : ses bornes hautes (`click<9`, `pygit2<1.19`, `disposable-email-domains==0.0.237`…) retiendraient les deps runtime de kenboard dans la venv de test, + boto3.
  - cache des résultats bruts par `(version guarddog, paquet==version)` dans `.cache/guarddog/results/` ; allowlist appliquée à chaque run (l'éditer ne demande pas de rescan).
  - règles bloquantes : `threat-*` + détecteurs de métadonnées ; `capability-*` (21/47 paquets sains déclenchent `capability-filesystem-read`) et `threat-npm-*` ignorées. Mesuré : les exclure au scan ne fait rien gagner (~4 min dans les deux cas), filtrage à l'évaluation.
  - `bundled_binary` éclaté en un finding par binaire : allowlister les lanceurs connus rebloque sur un nouveau `.exe`.
  - entrée d'allowlist sans `reason` → erreur ; entrée qui ne matche plus → `warning:` (⚠ dans publish).
  - stderr GuardDog (429 ecosyste.ms du détecteur RubyGems chargé au démarrage, timeouts whois) conservé dans `.cache/guarddog/last-stderr.log`, hors du log publish.
- `pyproject.toml` — script PDM `py-malware` ; `[[tool.kenboard.guarddog.allow]]` : 9 entrées / 20 findings, chacune lue : python-dotenv (`.env`, raison d'être), flask (`flask run` charge `.env`), authlib (`AUTHLIB_INSECURE_TRANSPORT`), pyyaml (`__import__` du loader non sûr — kenboard n'appelle que `yaml.safe_load`, vérifié), werkzeug (eval de la console debugger, mode debug seulement), idna + pip vendored idna (table UTS #46), pip/distlib (`~/.pypirc`), pip `bundled_binary` (6 lanceurs Windows distlib).
- `publish.sh` — step « Malicious Package Scan (guarddog) » après pip-audit, commentaire : un hit = release compromise (stop, alerter) ou faux positif à allowlister **après lecture du code** ; `STEPS` 26/28/39/42 → 28/30/41/44 (avec #1242), 44 `print_step` = release non-CI.
- `.gitignore` — `.cache/`.
- `tests/unit/test_dep_gates.py` (nouveau, partagé avec #1242) — parsing des pins, requirements inconditionnels, règles bloquantes, `match` affiché, `bundled_binary` par fichier, allowlist (fichiers exacts, usage, reason obligatoire), validité de l'allowlist livrée.
- `doc/code-quality.md` § *Chaîne d'approvisionnement des dépendances* ; `CLAUDE.md` (commande + consigne : un échec GuardDog = compromission ou faux positif à allowlister après lecture).

### Comportements obtenus

- Scan à froid : 48 paquets, 4 min 38, 15 findings bloquants → tous lus et qualifiés faux positifs → allowlist.
- À chaud : `GuardDog 3.2.0: 0 blocking, 20 allowed — 48 packages (0 scanned, 48 cached)` en 1,5 s.
- CI (`publish.sh --ci`, Python 3.13 / ubuntu) : cache froid à chaque run (~4-5 min). Roues manylinux cp313 vérifiées sur PyPI pour les deps natives (yara-python 4.5.4, pygit2 1.18.2, nono-py 0.16) — pas encore exécuté sur le runner.

### Garde-fous

- `sh publish.sh --quality` : **30/30 vert**, aucune ligne ⚠ — deptry, pip-audit, guarddog, scorecard, mypy 0, interrogate 100 %, ruff/flake8/refurb/vulture clean, npm audit 0, vitest 82, VS Code 17, pytest 844, E2E 52, metrics gate PASS.
- scripts : `ruff check` clean, `mypy --strict` 0, `tests/unit/test_dep_gates.py` 19 passed.
- Limites connues : whois des domaines mainteneurs parfois en timeout sans erreur remontée par GuardDog (faux négatif possible sur `unclaimed_maintainer_email_domain`) ; dev-deps hors périmètre.
---

[← retour à quality](index.md) · [voir log](../log/2026-11-25.md)
