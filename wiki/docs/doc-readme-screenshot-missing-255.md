---
id: 255
title: "DOC / README / Screenshot missing"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:49
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: docs
section_title: "Documentation"
---

# #255 — DOC / README / Screenshot missing

Le README fait référence à des screenshots qui ne sont pas présents. corriger le problème

---

## Résolution

### Diagnostic

Le `README.md` contient `<img src="./doc/images/kanban.png">` (ligne 35) ainsi qu'une note `Regenerate the screenshot after a UI change: pdm run screenshots`. Or le répertoire `doc/images/` n'existait pas du tout dans le dépôt — le fichier `kanban.png` n'avait jamais été généré ni committé. Le script `pdm run screenshots` (`scripts/screenshots.py`) est en place et fonctionnel ; il manquait simplement son artefact de sortie.

### Modifications

- `doc/images/kanban.png` (nouveau, ~149 KB, 1600x1800) — capture générée par `pdm run screenshots` à partir de la base de test seedée (catégorie Tech avec projet "Kenboard" peuplé sur les 4 colonnes : todo / doing / review / done). Servi par GitHub via le chemin relatif déjà référencé dans le README.

Aucune modification de code, de Markdown ou de configuration : seul l'asset manquant a été ajouté.

### Comportements obtenus

- `README.md` rend désormais correctement la capture sur GitHub et PyPI (chemin relatif `./doc/images/kanban.png` résolu).
- Le script `pdm run screenshots` reste la source de vérité pour régénérer l'image après un changement d'UI (note déjà présente dans le README, inchangée).
- `git check-ignore doc/images/kanban.png` → exit 1 : le fichier n'est pas ignoré, il sera bien tracké.

### Garde-fous

- `pdm run screenshots` exécuté de bout en bout : reset + seed du test DB → boot Flask sur 5077 → Playwright → `wrote doc/images/kanban.png`. Pas d'erreur.
- Inspection visuelle de l'image : kanban Tech rempli (8 tâches sur 4 colonnes), kanban API publique vide avec l'état "Tout est clair pour le moment", header KENBOARD v0.1.84 + onglets de catégories. Conforme à ce qu'attend le README.
- Pas d'autre quality gate exécutée (aucun code modifié).

### Hors périmètre (non traité)

Le README référence également `doc/ken-cli.md`, `doc/api.md`, `doc/openapi.yaml`, `doc/oidc-adfs.md` qui n'existent pas non plus. Ces liens cassés ne sont pas couverts par le scope de la tâche (intitulée "Screenshot missing") — à traiter dans une tâche séparée si souhaité.
---

[← retour à docs](index.md) · [voir log](../log.md)
