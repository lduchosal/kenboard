---
id: 253
title: "UX / Shortcut / Retour d'experience"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:48
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/ux
section_title: "UX / interactions"
---

# #253 — UX / Shortcut / Retour d'experience

## Retour d'expérience original

After the pointer has been clicked at an item in the list, the Enter shortcut does not work in list anymore

On ne peut pas passer au board suivant. Arrivée en bas de la liste des tâches, on ne peut pas passer au board suivant.

Dans la home page, la navigation dans les items du début de page ne fonctionne pas

Le menu pour amener à l'administration pourrait avoir ses propres shortcut :
cmd+b  : admin board
cmd + u : admin user
cmd a : admin api
cmd q : déconnexion

Un bouton aide pourrait être ajouté dans le header pour montrer la popup des raccourcis claviers

Mettre à jour la documentaion des raccourcis claviers

---

## Résolution

### Modifications

- `src/dashboard/static/js/keyboard.js` : refonte de la couche de sélection.
  - **(#1)** Garde anti-double-fire sur Enter quand `e.target` est une `.kanban-task` focused : on laisse l'`onkeydown` natif de la carte gérer (sinon toggleDetail tournait deux fois et s'annulait).
  - **(#2)** `moveVertical(±1)` au bord d'une colonne : tente de sauter au `.kanban` adjacent (premier card de la suivante avec `+1`, dernière avec `-1`). Si pas de board adjacent, clamp.
  - **(#3)** Modèle de sélection généralisé : nouveau sélecteur `NAV_SELECTOR = '.kanban-task:not(.task-hidden), [data-kb-nav]:not(.task-hidden)'`. `selected()` (générique) + `selectedCard()` (narrow .kanban-task uniquement). Hors d'un `.kanban-tasks`, ↑↓ et ←→ tombent sur `moveFlat()` (DOM order).
  - **(#3)** `actionOpen()` : `.kanban-task` → toggleDetail ; `<a>` avec `href` → click() (navigation native) ; `[data-kb-href]` → location.href.
  - **(#4)** `g`-prefix étendu : `g h` accueil, `g b` admin board, `g u` admin users, `g k` admin keys (api), `g l` déconnexion (submit du formulaire `.logout-form` car POST CSRF-protégé).
- `src/dashboard/templates/index.html` : `data-kb-nav` ajouté sur `.cat-card` pour activer la nav clavier sur la home page.
- `src/dashboard/templates/partials/header.html` : nouveau bouton `?` (`.kb-help-btn`) à côté de l'avatar, ouvre la modal d'aide (#5).
- `src/dashboard/static/style.css` : styles pour `.kb-help-btn` (rond, dimmed, hover accent).
- `src/dashboard/templates/modals/keyboard.html` : sections ajoutées pour *Page d'accueil*, *Navigation entre boards*, et l'admin (g+b/u/k/l) (#6).
- `src/dashboard/static/js/keyboard.test.js` : 7 nouveaux tests couvrant le spill-over entre kanbans + flat nav home page (total 17 tests).

### Comportements obtenus

- Cliquer une carte puis Enter : ouvre/ferme le détail une seule fois (bug #1 corrigé).
- ↓ en bas de la dernière carte d'une colonne : passe à la première carte du board suivant. ↑ en haut : passe à la dernière carte du board précédent.
- Sur la home page : ↑↓←→ navigue entre les `.cat-card` ; Enter sur une card sélectionnée navigue vers la catégorie.
- `g b` → /admin/board, `g u` → /admin/users, `g k` → /admin/keys, `g l` → POST /logout, `g h` → /.
- Bouton `?` dans le header (à droite, avant l'avatar) ouvre la modal d'aide.
- Documentation des raccourcis à jour avec les nouvelles sections.

### Push-back accepté

Les `cmd+b/u/a/q` proposés sont réservés par le navigateur (cmd+a = select-all, cmd+q = quit, cmd+u = view source, cmd+b = bookmarks). On a utilisé le `g`-prefix existant à la place — même mémoire musculaire (Gmail / GitHub) sans conflit avec le navigateur.

### Garde-fous

- `pdm run js-test` : 17 passed (10 anciens + 7 nouveaux pour spill-over + flat nav)
- `pdm run js-lint` / `js-typecheck` / `js-build` : clean (bundle 22.93 KB / 6.44 KB gzip)
- `pdm run check` (composite) : 378 passed
- `pdm run test-e2e` : 52 passed / 0 failed
---

[← retour à frontend/ux](index.md) · [voir log](../../log.md)
