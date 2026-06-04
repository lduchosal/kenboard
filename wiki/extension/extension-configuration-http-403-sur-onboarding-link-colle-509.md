---
id: 509
title: "EXTENSION / Configuration : HTTP 403 sur onboarding link collé"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-29T09:59:24
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: extension
section_title: "Browser extension"
---

# #509 — EXTENSION / Configuration : HTTP 403 sur onboarding link collé

Quand on colle un onboarding link dans la nouvelle extension (champ Onboarding link, #504) puis qu'on teste/utilise, on obtient un "HTTP 403".

---

## Résolution

### Diagnostic (cause racine)
Le 403 vient du bouton "Test connection" de l'extension, PAS du token onboard.
- test() appelait `GET /api/v1/projects` (endpoint cross-projet, liste tous les projets).
- Dans auth._resolve_project_id (src/dashboard/auth.py), aucun cas ne couvre `GET /api/v1/projects` → retourne None → _enforce_api_key renvoie `403 {"error":"cannot resolve project for scope check"}` (auth.py:338-340).
- C'est vrai pour TOUTE clé bearer scopée par projet (dont le token onboard, key_type "onboarding", scope write sur 1 projet). Seules une session cookie ou la clé admin statique passent sur /api/v1/projects.
- Conséquence : le token onboard fonctionne pour le POST /api/v1/tasks (création réelle : _resolve_project_id lit body.project_id, scope write OK), mais le bouton Test échouait toujours en 403, donnant l'impression que la config est cassée.

### Modification
- extension/options.js — test() interroge désormais `GET /api/v1/tasks?project=<projectId>` au lieu de `GET /api/v1/projects`. Cet endpoint résout le project_id (auth.py:96-97) donc le scope-check passe ; il valide base URL + token + le scope du token sur le projet exact où atterriront les tâches. Le garde exige maintenant aussi projectId (rempli automatiquement par le collage du lien onboarding).

### Pourquoi pas de changement serveur
Le token onboard a déjà le bon scope (write). Le souci est uniquement que /api/v1/projects n'est pas scopable pour une clé per-projet. Corriger côté extension est minimal et aligne le test sur ce que l'extension fait réellement (POST /api/v1/tasks sur ce projet).

### Garde-fous
- Comportement serveur confirmé par tests/unit/test_api_keys.py::test_read_scope_can_get_but_not_post : clé scope read sur le projet → GET /api/v1/tasks?project=X = 200 (le token onboard a write ≥ read).
- node --check extension/options.js : OK. extension/ hors périmètre Biome ; style aligné sur l'existant.
- NON testé en navigateur ici (impossible de charger l'extension dans cet environnement) — vérifié par analyse du code d'auth + tests serveur existants. À confirmer par un Test connection réel après reload de l'extension.
- Note : le GET de test promeut le token onboarding → onboarded (auth.py:359) ; sans effet fonctionnel, le token reste valide.
---

[← retour à extension](index.md) · [voir log](../log/2026-05-29.md)
