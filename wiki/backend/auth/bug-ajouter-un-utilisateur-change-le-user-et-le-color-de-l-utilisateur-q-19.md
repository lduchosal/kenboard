---
id: 19
title: "BUG / Ajouter un utilisateur, change le user et le color de l'utilisateur Q"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:12
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #19 — BUG / Ajouter un utilisateur, change le user et le color de l'utilisateur Q

Dans la page d'édition des utilisateurs, ajouter un utilisateur a un comportement bizarre et écrase les informations de l'utilisateur Q.

## Cause root identifiée — Firefox form history

Le bug n'existe **que dans Firefox**. Reproduit avec playwright firefox sur le live :
- 1 seul `POST /api/v1/users` côté API (pas de PATCH sur Q)
- Q reste **intact en DB** — vérifié par curl
- Mais après le `location.reload()`, le DOM montre Q's row avec `name="FFRepro"` / `color="#abcdef"` (les valeurs du nouveau user)

**Mécanisme** : Firefox utilise sa **form history** pour autofiller tous les `<input type="text">` similaires d'une page après navigation. Comme `.u-name` (Q's row) et `#new-name` (add row) sont deux inputs text sans `name` attribute, Firefox les considère équivalents et réinjecte la valeur tapée précédemment dans `.u-name` au reload. L'utilisateur voit visuellement Q renommé, alors qu'en DB Q est intact.

Chromium et webkit n'ont pas ce comportement (4 scénarios testés sur chacun, Q intact).

## Fix

`templates/admin_users.html` :
- `autocomplete="off"` sur `.u-name`, `.u-color`, `#new-name`, `#new-color`
- `autocomplete="new-password"` sur les inputs password (block toute autofill de password manager)
- Bonus UX : bouton Créer en `btn btn-save` (bleu accent) au lieu de `.btn-edit` générique pour ne plus le confondre avec Enregistrer/Supprimer + ligne séparatrice avec label "NOUVEL UTILISATEUR"

## Tests de régression (3 nouveaux)

Dans `tests/e2e/test_dashboard.py::TestAdminUsers` :

1. **`test_create_user_does_not_modify_existing_users`** (chromium) — seed Alice/Bob/Q-admin, snapshot byte-pour-byte avant, crée Newbie, vérifie chaque user pré-existant est strictement identique
2. **`test_create_button_visually_distinct`** (chromium) — vérifie que `#users-create-btn` a la classe `btn-save`
3. **`test_firefox_create_user_no_autofill_leak`** (firefox via persistent context) — **le test critique pour ce bug**. Lance un vrai Firefox avec form history activée, seed Alice + Q-admin, crée "AutofillBait", vérifie qu'aucune row existante n'a été autofilled. **Vérifié bidirectionnellement** : sans `autocomplete="off"` le test échoue avec exactement le message du bug (`Firefox autofilled Q's name input: expected 'Q', got 'AutofillBait'`).

## État

- 93 tests verts (64 unit + 29 e2e)
- Tous les checks qualité passent
- Prêt pour publish 0.1.14
---

[← retour à backend/auth](index.md) · [voir log](../../log.md)
