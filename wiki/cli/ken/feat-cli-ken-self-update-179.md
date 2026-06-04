---
id: 179
title: "FEAT / CLI / ken self-update"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:40
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: cli/ken
section_title: "ken task CLI"
---

# #179 — FEAT / CLI / ken self-update

Nouvelle commande ken self-update qui met a jour kenboard depuis PyPI. Utilise sys.executable -m pip install --upgrade kenboard. Affiche la version courante, lance pip, confirme le succes. Met aussi a jour certifi et toutes les deps transitives.

---

## Resolution

- ken.py : nouveau command @cli.command(name='self-update') qui lance subprocess.run pip install --upgrade kenboard. Affiche la version courante avant et confirme apres.
- 269 tests verts.
---

[← retour à cli/ken](index.md) · [voir log](../../log/2026-05-24.md)
