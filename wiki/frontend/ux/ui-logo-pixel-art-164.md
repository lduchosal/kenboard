---
id: 164
title: "UI / LOGO / Pixel art"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:45
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/ux
section_title: "UX / interactions"
---

# #164 — UI / LOGO / Pixel art

je t'ai donné mon logo-robot2.svg, fait un rendu en PNG, et un  rescale pour le pixeliser en 32x32 et en faire un pixel art en svg genre pixel grid comme pour logo.svg

---

## Résolution

### Itérations

Plusieurs tailles testées (4096→128, 4096→32, 4096→24, 4096→16) et un swap de couleurs Swiss flag (robot blanc sur fond rouge). Après comparaison, le logo KEN original pixel-art a été préféré au robot — il donne une meilleure impression visuelle.

### Modifications conservées

- **`scripts/pixelart.py`** (nouveau) — script réutilisable pour générer du pixel-art SVG depuis un SVG vectoriel :
  ```sh
  python scripts/pixelart.py input.svg --size 24 --swap ff0000,ffffff --output logo.svg
  ```
  Options : `--size` (grille), `--render` (hi-res), `--swap` (remap couleurs bg,fg), `--background`, `--preview` (PNGs intermédiaires).

- **`README.md`** — layout deux colonnes (table HTML) : logo KEN à gauche (33%, 160px), badges à droite. Section "Usage pour les BOT" réécrite avec le flow d'onboarding automatique.

- **`logo.svg`** + **`static/logo.svg`** — restauré au KEN original pixel-art (le préféré).

### Fichiers nettoyés

Les fichiers intermédiaires des itérations (logo-robot2-*.png, logo-step*.png, logo-robot.svg, logo-robot2-pixel.svg, logo-robot2.svg) ont été supprimés du repo.

### Garde-fous

- 269 tests verts
- Le script `pixelart.py` reste disponible pour de futures tentatives de logo
---

[← retour à frontend/ux](index.md) · [voir log](../../log.md)
