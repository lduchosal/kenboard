---
id: 240
title: "QUALITY / Sonarcloud"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:59
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #240 — QUALITY / Sonarcloud

https://sonarcloud.io/project/overview?id=lduchosal_kenboard

---

## Resolution

5 issues restantes, 3 corrigees :

### Corriges

- **Web:MouseEventWithoutKeyboardEquivalentCheck + Web:S6848** (2) — scope-badge dans admin_users.html : ajout role=button, tabindex=0, onkeydown pour Enter/Space
- **javascript:S3776** (1) — toggleDetail complexite 19 : extrait _lazyLoadDesc() reutilise aussi par _applyTaskHash()

### Non corriges (acceptes)

- **jssecurity:S8476** — 'tainted data' dans openEditTask. False positive : le task ID vient du data-task-id interne, pas d'input utilisateur.
- **javascript:S7785** — 'prefer top-level await'. _applyTaskHash() n'est pas dans un ES module, top-level await n'est pas applicable.

### Garde-fous

- pytest unit : 368 passed
---

[← retour à quality](index.md) · [voir log](../log/2026-05-24.md)
