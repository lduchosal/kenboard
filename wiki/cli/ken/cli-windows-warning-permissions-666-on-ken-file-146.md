---
id: 146
title: "CLI / WINDOWS / Warning permissions 666 on .ken file"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:36
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: cli/ken
section_title: "ken task CLI"
---

# #146 — CLI / WINDOWS / Warning permissions 666 on .ken file

Sur Windows, le CLI ken emet un warning :
Warning: .ken has mode 666, expected 600 (user only) ...

Sous windows le mode 666 ne veux rien dire
icalcls .ken /ihneritance:r /grant:r "user" ne fonctionne pas

---

## Résolution

### Diagnostic

Sur Windows, `os.stat().st_mode` retourne toujours `0o666` et `os.chmod(0o600)` est un no-op — les permissions POSIX n'existent pas sur NTFS. Le warning se déclenchait à chaque exécution de `ken` sans aucun fix possible côté utilisateur (`icacls` ne fonctionne pas de manière fiable depuis Python).

### Options évaluées

- **A. Skip sur Windows** — retourner immédiatement si `sys.platform == "win32"`. Pragmatique : le dossier profil utilisateur Windows est déjà protégé par les ACLs NTFS par défaut. ✅ **Retenue**
- **B. icacls** — fragile (noms d'utilisateur avec espaces/accents, domaines AD, dépend du PATH). ❌ Confirmé non-fonctionnel par le reporter.
- **C. pywin32** — dépendance lourde pour un best-effort. ❌ Écarté.

### Modification

- **`src/dashboard/ken.py`** — `_check_ken_permissions()` retourne immédiatement si `sys.platform == "win32"`. Docstring mise à jour pour expliquer pourquoi.

### Garde-fous

- 265 tests verts, `pdm run check` OK
- Aucun changement de comportement sur Linux/macOS/FreeBSD (le check POSIX 0o600 reste actif)
---

[← retour à cli/ken](index.md) · [voir log](../../log.md)
