---
id: 499
title: "OPS / kenboard update / auto-update bloqué sur le marqueur last-attempted"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-28T17:56:50
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: ops
section_title: "Ops & deployment"
---

# #499 — OPS / kenboard update / auto-update bloqué sur le marqueur last-attempted

web2 (et tous les hôtes kenboard) ne se mettent pas à jour automatiquement : le service reste sur 0.1.111 alors que 0.1.112 est dispo.

## CAUSE RACINE (confirmée via le log)
Le pré-fetch du script update (`pip download 'kenboard[prod]==X'`) tente de COMPILER des deps C/Rust sans wheel FreeBSD sur PyPI : argon2-cffi→argon2-cffi-bindings→cffi → `cc: command not found`. Les hôtes n'ont PAS de compilateur. Idem attendu pour pymysql[rsa]→cryptography (Rust) et pydantic→pydantic-core (Rust). Le venv (80-kenboard.yml) est un virtualenv isolé : les C-exts avaient été compilées au provisioning (quand cc existait), mais rien ne peut les reconstruire ensuite.

## Effet de bord (back-off)
Le pré-fetch échoue → écriture de la version dans last-attempted-version → tous les ticks cron suivants sortent exit 0. D'où « refuse TOUJOURS ».

## Piège log → CORRIGÉ
Avant : deux fichiers — /var/log/kenboard-update.log (TIRET, sortie pip) vs /var/log/kenboard_update.log (UNDERSCORE, stdout cron/rc.d). Nommage trompeur. Désormais unifié sur l'unique /var/log/kenboard_update.log.

---

## Résolution (role ansible kenboard — Option A validée avec Luc)
Extensions C/Rust depuis pkg + venv system-site-packages + install online sans pré-fetch + log unifié.

### Modifications (../ansible/roles/kenboard/)
- defaults/main.yml : liste kenboard_pkg_python (py311-cffi, py311-argon2-cffi, py311-cryptography, py311-pydantic-core, py311-pydantic2, py311-yaml). ⚠ noms à confirmer (pkg search) — pydantic v2 = py311-pydantic2 probablement.
- tasks/20-pkg.yml : tâche pkgng bouclant sur kenboard_pkg_python.
- tasks/80-kenboard.yml : virtualenv_site_packages: true (venv --system-site-packages → pip voit les C-exts pkg comme satisfaites, ne compile rien).
- files/kenboard/update : pré-fetch pip download + install offline supprimés → pip install --upgrade --upgrade-strategy only-if-needed --no-cache-dir online. En-tête réécrit (#499). Back-off marker conservé.
- files/kenboard/update + cron.d/kenboard : LOG UNIFIÉ sur l'unique /var/log/kenboard_update.log (underscore, comme kenboard_snapshot.log). Variable update_log (hyphen) supprimée ; pip/migrate écrivent sur stdout/stderr → captés par la redirection cron. Plus de double fichier.

### Comportements obtenus
- Install initiale ET auto-update ne nécessitent plus de compilateur.
- pip ne fetch que les wheels pure-python → fenêtre service-down courte malgré la suppression du pré-fetch.
- Un seul fichier de log update, lisible (progress + sortie pip dans l'ordre chrono).

### Garde-fous
- sh -n OK sur le script update. Aucune réf résiduelle à update_log/hyphen. Pas de suite de tests ansible.

### RESTE À FAIRE (action Luc / déploiement — non fait)
1. Confirmer les noms de paquets pkg sur web2 (pkg search py311-pydantic2 / cffi / cryptography / pydantic-core / yaml).
2. svn ci des changements ansible.
3. Déployer sur UN host d'abord (web2) : la tâche 'Clean venv' recrée le venv → install initiale rejouée. Vérifier le redémarrage du service.
4. Déblocage immédiat web2 si besoin : rm /var/tmp/kenboard-update/last-attempted-version puis upgrade manuel online.
---

[← retour à ops](index.md) · [voir log](../log.md)
