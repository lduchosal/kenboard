---
id: 157
title: "BUG / E2E / Régressions tests e2e après fullscreen modal #155"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:40
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #157 — BUG / E2E / Régressions tests e2e après fullscreen modal #155

9 tests e2e en échec (TimeoutError) dans TestTaskCRUD après l'ajout du bouton fullscreen dans task_card.html. Les tests qui ouvrent le modal d'édition via double-clic échouent probablement parce que le nouveau bouton ⤢ intercepte le clic ou que le sélecteur Playwright pour le bouton Editer est ambigu.

Tests en échec :
- test_edit_task
- test_delete_task
- test_duplicate_task
- test_project_default_who_prefills_edit_modal_when_who_empty
- test_edit_modal_keeps_existing_who
- test_move_task_via_status_select
- test_edit_modal_status_reflects_dragged_position
- test_task_description_renders_markdown
- test_task_description_xss_is_sanitized
---

[← retour à quality](index.md) · [voir log](../log.md)
