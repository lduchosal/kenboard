---
id: 293
title: "QUALITY / Clean unwanted files"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:30:00
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #293 — QUALITY / Clean unwanted files

## Demande

Remove unwanted files from repo: \`.DS_Store\` (committed) and add gitignore entries for OS / editor noise.

---

## Résolution

### Modifications

- `.gitignore` : nouvelle section *OS / editor noise* ajoutant `.DS_Store`, `Thumbs.db`, `*.swp`, `.vscode/`.
- Untrack du `.DS_Store` à la racine (`git rm --cached`).

### État avant

```
$ git ls-files | grep -iE "\.DS_Store|Thumbs\.db|\.idea|\.vscode|__pycache__"
.DS_Store
```

`.idea/`, `__pycache__/`, `.venv/` étaient déjà couverts par le gitignore et non trackés.

### État après

- `.DS_Store` supprimé du tracking et du working tree.
- `.gitignore` couvre désormais aussi `Thumbs.db` (Windows), `*.swp` (vim swap), `.vscode/` (settings IDE).

### Garde-fous

- `pdm run check` : 394 passed (0 régression)
- Aucun fichier de test impacté — pure cleanup.
---

[← retour à quality](index.md) · [voir log](../log.md)
