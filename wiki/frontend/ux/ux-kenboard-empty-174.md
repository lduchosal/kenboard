---
id: 174
title: "UX / KENBOARD / Empty"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:39
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/ux
section_title: "UX / interactions"
---

# #174 — UX / KENBOARD / Empty

Quand on est dans un kenboard d'une categorie et qu'il n'y a pas de projet, il faudrait afficher un message d'aide avec un lien vers la page d'admin des categories et projets. Idem quand on est sur la home page et qu'il n'y a pas de categorie.

---

## Resolution

### Template reutilisable

Nouveau partial `partials/empty_state.html` avec variables Jinja :
- `es_badge` : label uppercase (ex: Plateforme Kanban, Administration)
- `es_title` : titre principal
- `es_subtitle` : paragraphe explicatif
- `es_cards[]` : liste de cartes {icon, color, title, text, tag}
- `es_cta` : bouton {label, href}

Style editorial inspire de doc/uxui/empty : cartes arrondies 16px, icones colorees (blue/purple/amber), ombre ambiante, badge violet, bouton gradient.

### 5 pages equipees

| Page | Condition | Contenu |
|---|---|---|
| Home (index.html) | Pas de categories | 3 cartes (Categories, Projets, Taches) + CTA Configurer le board |
| Categorie (category.html) | Pas de projets actifs ni archives | 2 cartes (Projet=Kanban, Taches) + CTA Configurer le board |
| Admin board (admin_board.html) | Pas de categories | 3 cartes (setup steps) + CTA + Categorie (ouvre le modal) |
| Admin users (admin_users.html) | Pas d'utilisateurs | 2 cartes (Utilisateurs, Mot de passe) |
| Admin API keys (admin_keys.html) | Pas de cles | 3 cartes (Token, Securite, Expiration) |

### CSS

Bloc .es (empty state) dans style.css : max-width 860px, grille responsive auto-fit minmax(200px, 1fr), cartes .es-card avec bg #faf1fa, icones .es-card-icon avec 3 couleurs, badge .es-badge violet, bouton .es-cta-btn gradient bleu. Responsive a 640px.

### Garde-fous

- 269 tests verts
- Aucune API modifiee, aucune migration
---

[← retour à frontend/ux](index.md) · [voir log](../../log/2026-05-24.md)
