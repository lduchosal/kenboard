# Project Dashboard

[![PyPI version](https://img.shields.io/pypi/v/kenboard.svg)](https://pypi.org/project/kenboard/)
[![Python versions](https://img.shields.io/pypi/pyversions/kenboard.svg)](https://pypi.org/project/kenboard/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Build](https://github.com/lduchosal/kenboard/actions/workflows/python-package.yml/badge.svg)](https://github.com/lduchosal/kenboard/actions/workflows/python-package.yml)
[![Publish](https://github.com/lduchosal/kenboard/actions/workflows/publish.yml/badge.svg)](https://github.com/lduchosal/kenboard/actions/workflows/publish.yml)
[![codecov](https://codecov.io/gh/lduchosal/kenboard/branch/main/graph/badge.svg)](https://codecov.io/gh/lduchosal/kenboard)
[![Docstring coverage](./interrogate_badge.svg)](./interrogate_badge.svg)
[![Downloads](https://static.pepy.tech/badge/kenboard)](https://pepy.tech/project/kenboard)

Tableau de bord de suivi de projets avec vue par categories et kanbans.

## Structure

```
dashboard/
├── build.py          # Generateur de pages statiques
├── data.json         # Donnees source (categories, projets, taches)
├── style.css         # CSS partage par toutes les pages
├── index.html        # Dashboard (genere)
└── cat/              # Pages detail par categorie (generees)
    ├── immobilier.html
    ├── sante.html
    ├── technique.html
    ├── famille.html
    ├── finance.html
    └── education.html
```

## Usage

Editer `data.json` puis regenerer :

```sh
python3 build.py
```

Ouvrir `index.html` dans un navigateur. Aucun serveur requis.

## Pages

### Dashboard (`index.html`)

- Header sticky avec badges categorie cliquables
- 6 cartes categorie en grille 2x3
- Chaque carte : nom, nombre de taches ouvertes, burndown agrege, liste des projets (acronymes 3 lettres)
- Clic sur une carte -> page detail categorie
- Clic sur un acronyme projet -> ancre dans la page detail

### Detail categorie (`cat/{id}.html`)

- Header identique au dashboard
- Un kanban par projet avec 4 colonnes : A faire, En cours, Revue, Fait
- Sous-titres projet sticky sous le header
- Colonne "Fait" limitee a 5 cartes + "voir plus"

## Cartes kanban

3 modes d'affichage :

| Mode | Contenu | Usage |
|------|---------|-------|
| **Normal** | Titre, description courte | Vue par defaut |
| **Detail** | Titre, description complete, avatar, date | Carte selectionnee (lecture) |
| **Edit** | Champs editables (titre, detail, qui, quand), boutons Annuler/Enregistrer | Carte en edition |

Chaque carte affiche :
- **Quoi** : titre (gras) + description
- **Qui** : avatar cercle colore avec initiale (visible en mode detail)
- **Quand** : date au format `dd.mm` (visible en mode detail)

## Responsive

4 breakpoints :

| Breakpoint | Cible | Dashboard | Kanban |
|-----------|-------|-----------|--------|
| > 768px | Desktop | 2 colonnes categories | 4 colonnes |
| <= 768px | Tablet | badges -> dropdown, acronymes projets | 3 colonnes (En cours + Revue empilees) |
| <= 640px | Mobile | 1 colonne categories | 2 colonnes (A faire + reste empile) |
| <= 480px | Small mobile | 1 colonne categories | 1 colonne |

## Donnees (`data.json`)

### Categories

```json
{
  "id": "technique",
  "name": "Technique",
  "color": "var(--accent)"
}
```

Couleurs disponibles : `--orange`, `--green`, `--accent` (bleu), `--purple`, `--cyan`, `--red`.

### Projets

```json
{
  "id": "slug-du-projet",
  "name": "Nom complet",
  "acronym": "ACR",
  "cat": "technique",
  "done": 18,
  "total": 25,
  "due": "2026-05-15",
  "ideal": [25, 23, 20, ...],
  "actual": [25, 24, 22, ...],
  "tasks": [
    { "title": "Titre", "desc": "Description", "status": "todo", "who": "Q", "when": "2026-04-15" }
  ]
}
```

Statuts : `todo`, `doing`, `review`, `done`.

### Burndown

Les champs `ideal` et `actual` sont des tableaux de taches restantes par semaine. Le burndown affiche `actual` avec la couleur de la categorie.

### Indicateur de sante projet

Le point colore a gauche de chaque acronyme dans le dashboard :
- **Gris** : aucune tache en cours
- **Couleur categorie** (intensite variable) : taches en cours (plus il y en a, plus la couleur est saturee)

## Avatars

Les avatars sont des cercles colores avec l'initiale. Les couleurs sont definies dans `build.py` :

```python
AVATAR_COLORS = {
    "Q": "#0969da",
    "Alice": "#8250df",
    "Bob": "#bf8700",
    "Claire": "#1a7f37",
}
```

## Dependencies

- Python 3.6+
- Aucune dependance externe
