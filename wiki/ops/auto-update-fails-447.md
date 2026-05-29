---
id: 447
title: "AUTO update fails"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-25T14:31:22
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: ops
section_title: "Ops & deployment"
---

# #447 — AUTO update fails

WARNING: Retrying (Retry(total=4, ...)) after connection broken by 'NewConnectionError(... Failed to establish a new connection: [Errno 65] No route to host)': /simple/kenboard/
[... 5 retries ...]
Requirement already satisfied: flask>=3.1 in ./usr/local/kenboard/venv/lib/python3.11/site-packages (from kenboard[prod]) (3.1.3)
[... toutes les deps "already satisfied" ...]

---

## Résolution

### Root cause

Le script `roles/kenboard/files/kenboard/update` (ansible) stoppe le
service AVANT de parler à PyPI. Quand `pip install --upgrade
kenboard[prod]` rencontre un "No route to host", il enchaîne 5 retries
(~50s chacun) — fenêtre 502 visible côté client. Pire, à l'épuisement
des retries pour le package principal, pip continue avec les
dépendances ("already satisfied") et exit 0 SANS avoir upgradé
kenboard. Le script croit que tout est OK, le cron retente la minute
suivante, boucle infinie de 502.

### Modifications

- `roles/kenboard/files/kenboard/update` (SVN rev 569) — refonte complète :
  - **Pré-fetch wheel avant stop service** : la phase réseau-risquée
    (`pip download --dest /var/tmp/kenboard-update`) tourne avec le
    service UP. Aucun 502 pendant les retries pip.
  - **Install offline + pin** : `pip install --no-index --find-links
    /var/tmp/kenboard-update 'kenboard[prod]==<target>'` — déterministe,
    rapide, pas de fallback "already satisfied" possible.
  - **Vérification post-install** : compare `pip show kenboard` à la
    version cible ; si différent → ERROR + restart service.
  - **Back-off marker** : `/var/tmp/kenboard-update/last-attempted-version`
    enregistre la version qui a échoué. Le cron skip silencieusement
    cette version jusqu'à ce qu'une nouvelle release ou un `rm` du
    marker libère le retry. Plus de boucle 502.
  - **Log dédié** : `/var/log/kenboard-update.log` capture la sortie pip
    complète (au lieu de `/dev/null` avant) pour le debug post-mortem.

- `roles/kenboard/tasks/80-kenboard.yml` (SVN rev 569) — ajoute `update`
  au loop `Copy scripts` (il en était absent, c'est pour ça que les
  anciens fix au script n'arrivaient jamais sur la box via `ab`).

### Déploiement

Hotfix appliqué via `ansible web2 -m copy -a "src=... dest=/usr/local/kenboard/bin/update ..."` par l'opérateur. Service jamais touché pendant le déploiement.

### Garde-fous

- Le nouveau script est rétro-compatible (mêmes interfaces : appelé
  par rc.d et cron, sortie sur stdout). Aucun changement de cron
  nécessaire.
- En cas de régression : `cp /usr/local/kenboard/bin/update.bak ...`
  ou redéployer la rév SVN précédente.
---

[← retour à ops](index.md) · [voir log](../log.md)
