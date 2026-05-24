---
id: 228
title: "PERF / Test de charge / 330K taches"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:53
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/perf
section_title: "Performance & observability"
---

# #228 — PERF / Test de charge / 330K taches

## Dataset de test de performance

Script `scripts/seed_perf_data.py` cree un dataset massif via l'API REST pour que le monitoring de performance (#214) observe les ecritures.

### Utilisation

```sh
# Seed complet (330K taches)
python scripts/seed_perf_data.py --config .ken3

# Volume reduit pour test rapide
python scripts/seed_perf_data.py --config .ken3 --cats 5 --projects 3 --tasks 10

# Nettoyage
python scripts/cleanup_perf_data.py --config .ken3
```

### Options

- `--config` : fichier .ken avec les credentials admin
- `--cats N` : nombre de categories (defaut 120)
- `--projects N` : projets par categorie (defaut 25)
- `--tasks N` : taches par projet (defaut 110)
- `--workers N` : threads concurrents (defaut 8)

### Interet

- Chaque POST passe par le middleware perf → performances de WRITE mesurees
- Le monitoring cree des taches PERF si des seuils sont depasses
- Les scripts sont reutilisables (seed + cleanup)
---

[← retour à backend/perf](index.md) · [voir log](../../log.md)
