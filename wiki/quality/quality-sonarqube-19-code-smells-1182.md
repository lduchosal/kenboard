---
id: 1182
title: "QUALITY / SONARQUBE / 19 code smells"
status: done
who: "Claude"
due_date: 
updated_at: 2026-11-15T11:05:16
classified_at: 2026-11-15T10:42:24
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #1182 — QUALITY / SONARQUBE / 19 code smells

**TL;DR** — 19 code smells SonarCloud publiés avec un gate vert : le « Sonar way » ne juge que le new code et tolère la dette tant que le ratio reste ≤ 5 % → les 19 smells sont corrigés (CSS sans `!important`, mouvement soumis à `prefers-reduced-motion`, SVG décoratifs en `aria-hidden`), et `sonar_gate.py` bloque désormais dès qu'il reste au moins 1 issue ouverte (PHILOSOPHY.md §1).

SonarCloud (`lduchosal_kenboard`) remonte **19 code smells** ouverts (relevé 2026-11-15, API `issues/search?types=CODE_SMELL&resolved=false`).

## Inventaire

### css:S9423 — `!important` (14, MAJOR) — `src/dashboard/static/style.css`
- l.528
- l.1990, 1991, 1994, 1998, 2010
- l.2138, 2139, 2140, 2141, 2142, 2143, 2144, 2149

→ résoudre le conflit de spécificité au lieu de forcer `!important`.

### css:S9440 — reduced-motion (1, MAJOR) — `src/dashboard/static/style.css`
- l.743 — animation/transition sans garde `@media (prefers-reduced-motion: reduce)`.

### Web:ImgWithoutAltCheck — `<svg>` sans nom accessible (4, MINOR)
- `src/dashboard/templates/partials/kanban.html` l.33, l.60
- `src/dashboard/templates/partials/empty_state.html` l.21
- `src/dashboard/templates/modals/confirm.html` l.5

→ `aria-hidden="true"` si décoratif, sinon `<title>` / `aria-label`.

## Critère de done
- 0 code smell ouvert sur SonarCloud après analyse CI.
- Pas de régression visuelle (e2e Playwright vert, vérif manuelle des blocs CSS touchés).
- `pdm run check` vert.

## Résolution

### Diagnostic — pourquoi `publish.sh` n'a pas bloqué
- `scripts/sonar_gate.py` ne lisait que le statut du quality gate par défaut « Sonar way ». Ses conditions portent toutes sur le **new code**, et la maintenabilité y est une **note de dette** (A = dette ≤ 5 %), pas un nombre de smells. 11 smells de new code = 55 min de dette = ratio 0,02 % → A → `PASSED`.
- `css:S9423` et `css:S9440` sont des règles récentes : Sonar date leurs issues à l'historique de la ligne (06.04.2026), donc hors new code.
- La CI n'envoyait pas `sonar.projectVersion` (analyses `not provided`) → la période new code `previous_version` est restée figée au 08.04.2026.
- Bref : SonarCloud mesurait, rien ne bloquait. C'est exactement la dérive décrite au §5 de PHILOSOPHY.md.

### Modifications
- `scripts/sonar_gate.py` — en plus du statut « Sonar way », exige **0 issue ouverte** sur `main` (tous types, code neuf et existant) et **0 hotspot TO_REVIEW**. Le rapport d'échec liste conditions, issues (règle + `fichier:ligne`) et hotspots. Une issue triée dans l'UI (faux positif / won't fix) sort du compte : c'est une décision humaine tracée.
- `.github/workflows/python-package.yml` — le job SonarCloud passe `-Dsonar.projectVersion=<__version__>`, pour que la période new code reparte à chaque release.
- `src/dashboard/static/style.css`
  - l.528 : `.btn-edit.section-onboard-btn:hover` (spécificité 0,3,0) bat `.btn-edit:hover` (0,2,0) déclaré plus loin → plus besoin de `!important`. Fusion avec la règle d'opacité du hover.
  - Suppression du CSS mort : `.section-edit-btn` et `.edit-mode .edit-row` (media 768). Ces classes n'apparaissent dans aucun template, JS ou test.
  - `.kanban-middle` / `.kanban-rest` (media 768/640) et bloc `@media print` (`.fullscreen-card`, `.fullscreen-actions`, `.modal-close`) : même spécificité, déclarés après les règles de base, sans style inline concurrent → `!important` superflus, retirés.
  - l.743 : la `transition: transform` de `.color-dot` passe sous `@media (prefers-reduced-motion: no-preference)`.
- `templates/partials/kanban.html` (×2), `partials/empty_state.html`, `modals/confirm.html` — SVG décoratifs (texte adjacent) : `aria-hidden="true" focusable="false"`.
- `doc/code-quality.md` — documente le gate Sonar à zéro et la seule échappatoire (triage humain).

### Comportements obtenus
- Le gate durci, lancé contre l'état SonarCloud actuel (HEAD 37d5bc4), **échoue** (exit 1) et liste les 19 issues. L'ancien gate affichait `PASSED`.
- Rendu inchangé : styles calculés comparés dans Chromium entre l'ancien et le nouveau `style.css`, sur 4 largeurs (1200/700/600/400) × écran/impression + hover du bouton onboard → **112 valeurs, 0 différence**. Le hover onboard reste à `--card`.
- `style.css` ne contient plus aucun `!important`.

### Garde-fous
- `pdm run check` : vert (716 tests, metrics-gate palier 5 PASS), sans warning dans le log.
- `pdm run test-e2e` : 52 passed.
- **Reste à confirmer côté CI** : 0 issue SonarCloud après le push. Le prochain `publish.sh` le vérifie lui-même : il bloquera tant qu'il reste une issue.

### Hors périmètre (observé)
- Il reste du CSS `.edit-mode` / `.kanban-task.edit-mode` (~l.1180–1545) qu'aucun template ni JS n'utilise : candidat à une carte de nettoyage.
---

[← retour à quality](index.md) · [voir log](../log/2026-11-15.md)
