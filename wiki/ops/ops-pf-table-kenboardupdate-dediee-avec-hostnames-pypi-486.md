---
id: 486
title: "OPS / pf / table kenboardupdate dediee avec hostnames PyPI"
status: review
who: "Claude"
due_date: 
classified_at: 2026-05-28T09:57:14
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: ops
section_title: "Ops & deployment"
---

# #486 — OPS / pf / table kenboardupdate dediee avec hostnames PyPI

Sortir kenboard de la table pf partagée `<git>` et lui donner sa propre table `<kenboardupdate>`, peuplée à partir des hostnames PyPI réels au lieu d'un wildcard `0.0.0.0/0`.

---

## Résolution

### Modifications (SVN rev 602, ansible)

- `roles/kenboard/templates/pf.conf.j2` : ajout d'une seconde rule :
  ```
  table <kenboardupdate> persist file "/usr/local/etc/pf.conf.d/kenboardupdate"
  pass out quick on {dmz} inet proto tcp from (dmz) to <kenboardupdate> port https keep state
  ```
- `roles/kenboard/files/pf.conf.d/kenboardupdate.domain` *(nouveau)* :
  liste les FQDN consommés par pip (`pypi.org`, `files.pythonhosted.org`).
  Consommé par `service pftable reload` qui résout en IPs Fastly.
- `roles/kenboard/files/pf.conf.d/kenboardupdate` *(nouveau)* :
  snapshot initial vide, sera populé au déploiement.
- `roles/kenboard/templates/rc.conf.j2` : ajout
  `pftable_tables="freebsdpkg ntp kenboardupdate"` pour que le cron
  `pftable cronreload` rafraîchisse régulièrement les IPs Fastly.
- `roles/kenboard/tasks/50-pfconf.yml` : copy des deux nouveaux
  fichiers vers `/usr/local/etc/pf.conf.d/` + step
  `service pftable reload` pour populer la table au déploiement.
- `roles/kenboard/files/kenboard/update` : retire complètement le
  bloc `ensure_firewall_open()` + variables `git_*_file`. Le script
  ne touche plus du tout pf — pur pip download/install/migrate/start.

### Comportements obtenus

- `<kenboardupdate>` est privée au rôle kenboard. Aucun voisin
  (jeff, etc.) ne peut la flush au mauvais moment.
- Surface outbound 443 rétrécie : depuis `0.0.0.0/0` vers les ~5-10
  IPs Fastly servant `pypi.org` + `files.pythonhosted.org`.
- `pftable cronreload` (déjà installé par le rôle `pftable`) refresh
  les IPs périodiquement, donc rotation Fastly suivie automatiquement.
- Plus aucun toggle pf depuis le script update — état stable.

### Déploiement

L'opérateur lance :
```sh
cd ../ansible
ab kenboard.yml -l web2
```

Pour valider sur web2 après deploy :
- `pfctl -t kenboardupdate -T show` → ~5-10 IPs Fastly
- `grep kenboardupdate /etc/rc.conf` → présent
- `service kenboard update` → passe en pré-fetch propre, sans 502

### Garde-fous

- `sh -n update` : OK (parse sans erreur)
- Rôle `git` intact (les autres consommateurs continuent de l'utiliser)
- `_yoyo migrate` non concerné (pure config pf)

### Hors scope

- Migration jeff (`<jeffupdate>` + `jeffupdate.domain`) — tâche dédiée
  si on veut aligner ensuite.
- Suppression de la table `<git>` du rôle `git` — reste pour les
  autres consommateurs non-migrés.
---

[← retour à ops](index.md) · [voir log](../log.md)
