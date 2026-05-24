---
id: 215
title: "AGENT / .ken2 file"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:50
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: cli/ken
section_title: "ken task CLI"
---

# #215 — AGENT / .ken2 file

Donner la possibilite de passer le .ken en parametre au cli pour avoir plusieurs boards possibles. Le .ken doit contenir une description du board target.

---

## Resolution

### Modifications

- `src/dashboard/ken.py` :
  - Ajout option `--config` au groupe CLI pour pointer vers un fichier .ken alternatif
  - `_load_config()` accepte `config_override` : si fourni, utilise ce fichier au lieu de chercher .ken dans les parents
  - `KenConfig` : ajout champ `description` lu depuis le fichier .ken
  - `init` : ecrit `description=<nom du projet>` dans le fichier genere

### Utilisation

```sh
# Board par defaut (.ken)
ken list

# Board alternatif
ken --config .ken2 list
ken --config /path/to/board.ken add 'titre' --who Claude
```

### Format du fichier .ken

```
project_id=uuid
base_url=https://...
description=Mon board local
api_token=kb_...
```

### Garde-fous

- pytest unit : 327 passed
- mypy : 0 issues
- flake8 : clean
---

[← retour à cli/ken](index.md) · [voir log](../../log.md)
