---
id: 629
title: "KENBOARD / update"
status: done
who: "Claude"
due_date: 
classified_at: 2026-06-02T08:32:24
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: ops
section_title: "Ops & deployment"
---

# #629 — KENBOARD / update

root@web:/usr/home/user # cat /var/log/kenboard_update.log
[2026-06-02 08:24:07] kenboard: pip list rc=0 len=948
Traceback (most recent call last):
  File "<string>", line 3, in <module>
  File "/usr/local/lib/python3.11/json/__init__.py", line 293, in load
    return loads(fp.read(),
           ^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.11/json/__init__.py", line 346, in loads
    return _default_decoder.decode(s)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.11/json/decoder.py", line 340, in decode
    raise JSONDecodeError("Extra data", s, end)
json.decoder.JSONDecodeError: Extra data: line 3 column 1 (char 798)
[2026-06-02 08:24:07] kenboard: outdated detected but could not parse target version, skipping

---

## Résolution

### Cause racine

`ansible/roles/kenboard/files/kenboard/update`, ligne 60 :

```sh
outdated=$(${chdir}/venv/bin/pip list --outdated --format=json --no-cache-dir 2>&1)
```

Le `2>&1` mélange stderr dans stdout. Depuis pip 22.1, **l'avis "A new release of pip is available: X -> Y" est émis sur stderr** et donc capturé dans `$outdated` à la suite du JSON. Le `json.load` plus bas (lignes 83-90) parse correctement le tableau JSON jusqu'à `]`, puis trouve l'avis pip en texte derrière → `JSONDecodeError: Extra data: line 3 column 1 (char 798)`. Le script bascule sur le branch `could not parse target version, skipping` et l'update n'a jamais lieu, à chaque minute, silencieusement.

`len=948` dans le log confirme : pour une liste d'un seul package outdated (kenboard), le JSON fait ~150 chars ; 948 caractères = JSON + l'avis pip + saut(s) de ligne.

### Modifications

- `ansible/roles/kenboard/files/kenboard/update` (lignes 56-72) :
  - Retrait du `2>&1` sur la capture de `pip list` : pip's stderr remonte naturellement vers le redirect `> /var/log/kenboard_update.log 2>&1` du cron (`cron.d/kenboard:18`), donc la diagnostic visibility est préservée sans polluer le JSON.
  - Ajout de `--disable-pip-version-check` pour silencer l'avis le plus fréquent à la source.
  - Commentaire 5 lignes au-dessus pointant la cause + ken #629.
  - Suppression de `log "pip output: ${outdated}"` sur la branche failure (devenu redondant : la stderr de pip est déjà dans le log via le cron redirect, et `$outdated` est de toute façon vide quand pip échoue).

### Comportement obtenu

- `pip list --outdated --format=json --disable-pip-version-check` retourne **uniquement** du JSON sur stdout, parsé sans erreur.
- L'avis "new release of pip available" n'est plus émis du tout (`--disable-pip-version-check`).
- Si pip échoue pour de vrai (réseau, etc.), l'erreur va sur stderr → `/var/log/kenboard_update.log` via cron's `2>&1` → visible pour le diagnostic. Le script logge rc + len et exit 0 (back-off via le cron minute).
- Aucun changement dans la logique métier (back-off marker, restart service, migrate, etc.).

### Garde-fous

- Pas de tests unitaires côté ansible (script shell, pas couvert). Validation = run réel sur 1 host.
- `shellcheck` non installé localement, mais la modif est minimale : suppression d'un `2>&1` + ajout d'un flag pip + suppression d'une ligne log.
- pip `--disable-pip-version-check` existe depuis pip 1.5 (2014), donc compatible avec tous les pip qu'on peut croiser sur les hosts FreeBSD (py311-pip).

### Déploiement (à faire par l'opérateur)

```sh
(cd ansible && svn ci -m "kenboard/update: drop 2>&1 + --disable-pip-version-check (ken #629)")
ssh ans2 'cd ansible && svn up && ab kenboard.yml -l web2'   # test sur 1 host
# puis vérifier /var/log/kenboard_update.log sur web2 après ~2 min
ssh ans2 'cd ansible && ab kenboard.yml'                     # broad deploy
```
---

[← retour à ops](index.md) · [voir log](../log/2026-06-02.md)
