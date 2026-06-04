---
id: 133
title: "UI / Login / Logo SVG"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:39
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/pages
section_title: "Page templates (Jinja2)"
---

# #133 — UI / Login / Logo SVG

Ajoute le logo de KENBOARD sur la page de login.
La page a deux panels adjacents
Le panel de gauche a le logo 
Le panel de droit a le formulaire de login

---

## Résolution

### Modifications

- **`src/dashboard/static/logo.svg`** (nouveau) — copie de `/logo.svg` (racine du projet, déjà référencée par le README) dans le dossier static de Flask. La duplication est volontaire : la racine sert le rendu README sur GitHub/PyPI, le static est nécessaire pour que Flask serve l'asset à `/static/logo.svg`. Si le logo évolue, mettre à jour les deux fichiers.
- **`src/dashboard/templates/login.html`** — ajout d'un `.login-logo-panel` avec `<img src="/static/logo.svg">` à côté du `.login-form-panel` qui contient le titre + le formulaire existant à l'identique. Le wrapper extérieur garde la classe `.login-card`.
- **`src/dashboard/static/style.css`** :
  - `.login-logo-panel` : `background: var(--bg)`, `aspect-ratio: 1/1` (carré), `overflow: hidden`, `position: relative` (ancre pour le pseudo-élément)
  - `.login-logo-panel::after` : pseudo-élément en `position: absolute; inset: 0` avec un double `box-shadow: inset` (`0 2px 8px rgba(0,0,0,0.22)` + `0 0 0 1px rgba(0,0,0,0.08)`) pour donner l'impression que le logo est enfoncé sous la surface du card. Astuce nécessaire parce que `box-shadow: inset` ne fonctionne pas directement sur un `<img>` (le contenu de l'image masque l'ombre).
  - `.login-logo` : `width: 100%; height: 100%; object-fit: contain; border-radius: 8px` pour matcher le rayon du card.
  - `.login-form-panel` : `padding: 32px 36px 32px 54px; display: flex; flex-direction: column; justify-content: center` pour centrer verticalement le formulaire.
  - Bloc `.login-card-split` (legacy de l'itération précédente) conservé dans le CSS mais non référencé par le HTML — sans impact visuel, à nettoyer dans un prochain passage si besoin.
- **`tests/unit/test_auth_user.py`** — 2 tests ajoutés dans `TestLoginFlow` :
  - `test_get_login_renders_logo_panel` : vérifie que la page `/login` contient `login-card`, `login-logo-panel` et la balise `<img src="/static/logo.svg">`
  - `test_logo_static_asset_is_served` : GET `/static/logo.svg` retourne 200 avec un body qui contient `<svg` (vérifie que l'asset est réellement servi par Flask)

### Comportements obtenus

- La page `/login` affiche le logo Kenboard à côté du formulaire dans un card unique.
- Le logo est arrondi (rayon 8px) avec une ombre intérieure qui simule de la profondeur (logo "enfoncé" sous la surface du card).
- Le formulaire est inchangé : mêmes champs, mêmes validations, même action POST, même gestion d'erreur, même `next_url`.
- L'asset SVG est servi via le `static_folder` standard de Flask, pas besoin d'une nouvelle convenience route à la racine.

### Garde-fous

- `pdm run check` (composite isort, format, docformatter, typecheck, flake8, interrogate, refurb, lint, vulture, test-quick) → ✅ vert
- 246 tests unitaires verts (+2 vs baseline)
- Aucune nouvelle dépendance Python, aucun changement d'API, aucun changement de schéma DB
- Commit `137fd69` sur `main`, pushé vers `origin/main`

### Itérations notables (pour mémoire)

Plusieurs allers-retours sur le layout pendant la PR :
- d'abord deux panneaux côte à côte via Flexbox → le logo n'apparaissait pas en desktop (problème de hauteur intrinsèque SVG sans `width`/`height` HTML attrs dans un parent flex sans hauteur définie)
- puis CSS Grid `300px 1fr` qui a résolu la géométrie déterministe
- ajout de l'ombre intérieure et du rayon
- Q a finalement simplifié le HTML en gardant uniquement `.login-card` autour des deux divs enfants, ce qui est l'état final committé

### Hors scope

- Refacto de `.login-card-split` (CSS legacy) → garder pour un nettoyage groupé si une autre tâche UI tombe sur le login
- Mode sombre / thème custom → réutilisation des variables CSS existantes (`var(--card)`, `var(--bg)`, `var(--border)`)
- Logo SVG → asset existant inchangé, juste copié dans le dossier static
---

[← retour à frontend/pages](index.md) · [voir log](../../log/2026-05-24.md)
