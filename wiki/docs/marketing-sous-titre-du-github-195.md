---
id: 195
title: "MARKETING / Sous titre du github"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:44
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: docs
section_title: "Documentation"
---

# #195 — MARKETING / Sous titre du github

Le sous titre qui apparait dans la description github est Kanban et Dashboard. Il ne reflète pas correctement l'ambition du projet. Mettre à jour.

---

## Résolution

### Modifications

- Description GitHub mise à jour via `gh repo edit` :
  - Avant : `Kanban & Dashboard`
  - Après : `Self-hosted kanban bridging humans and AI coding agents (Claude Code, GPT): humans create and close tasks, agents claim them and move todo → doing → review via the 'ken' CLI. Per-project scoped API keys, OIDC, REST + CLI.`

### Comportements obtenus

- Le sous-titre explique les interactions entre les 3 acteurs (humains, agents, tâches) et le workflow de collaboration : humains créent/ferment, agents travaillent les colonnes intermédiaires via la CLI `ken`.
- Mentions des features enterprise clés (API keys scoped, OIDC) pour signaler le positionnement self-hosted.

### Garde-fous

- Vérification via `gh repo view --json description`
---

[← retour à docs](index.md) · [voir log](../log/2026-05-24.md)
