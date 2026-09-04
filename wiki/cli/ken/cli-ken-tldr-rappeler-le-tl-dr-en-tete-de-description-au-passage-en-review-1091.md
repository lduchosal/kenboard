---
id: 1091
title: "CLI / ken tldr : rappeler le TL;DR en tête de description au passage en review"
status: done
who: "Claude"
due_date: 
updated_at: 2026-09-04T10:22:16
classified_at: 2026-09-04T10:01:20
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: cli/ken
section_title: "ken task CLI"
---

# #1091 — CLI / ken tldr : rappeler le TL;DR en tête de description au passage en review

**TL;DR** — Rien ne poussait l'agent à résumer sa tâche : le rappel de passage en
review réclamait un trail de résolution, jamais une synthèse. `ken move --to review`
(et `ken update --status review`) demandent désormais un **TL;DR en tête de
description** ; `agent_guide.md` et `CLAUDE.md` documentent la forme, et le rappel
cesse au passage de recommander l'idiome `--desc "…\n…"` que le guide interdit.

## Demande

Quand l'agent passe un ken en review, lui rappeler d'ajouter un **TL;DR en début
de description** pour faciliter la compréhension de la tâche.

## Analyse

Trois surfaces portent aujourd'hui la consigne « comment shaper la description
avant review » :

1. `src/dashboard/ken/task_edit.py:224` — `_review_update_reminder()` : bloc
   stderr imprimé par `ken move <id> --to review` (`tasks.py:179`) **et**
   `ken update <id> --status review` (`task_edit.py:220`). Il dicte déjà la
   forme (original verbatim + `## Résolution` → Modifications / Comportements
   obtenus / Garde-fous). C'est le seul endroit où l'agent est interpellé au
   bon moment, et il écrit sur stderr pour ne pas corrompre `--json`.
2. `_wiki_groom_reminder()` (même fichier, l.241) — second bloc stderr, hors
   sujet ici.
3. `src/dashboard/agent_guide.md` (servi par `ken help`) — étape 4 « Update the
   task description BEFORE moving to review », son squelette `--desc-file`, et
   le cheatsheet (~l.156).

Le TL;DR n'existe nulle part dans le repo (aucune occurrence). La description
est aussi le corps rendu par `ken wiki sync` → `wiki_detail.py` : un TL;DR en
tête profite au board **et** aux pages wiki publiées.

Point d'attention : la règle en vigueur est « préserver la description d'origine
verbatim ». Un TL;DR **préfixé** (avant l'original) la respecte — on n'édite
rien, on ajoute une entête.

## Modifications proposées

### 1. `src/dashboard/ken/task_edit.py` — étendre `_review_update_reminder()`

Pas de 3e bloc stderr : la consigne TL;DR fait partie du même « shape ta
description ». Texte cible :

```
Reminder: update task #<id> with the implementation trail before review:
    ken show <id>                        # read the original description
    ken update <id> --desc-file <file>   # TL;DR + original + Résolution
Start with a TL;DR (1-2 lignes : problème → ce qui a été fait), keep the
original description intact below it, then append a Résolution section with
Modifications (files + one-line summary), Comportements obtenus, Garde-fous.
```

Forme documentée :

```markdown
**TL;DR** — <problème en une phrase> → <ce qui a été fait / obtenu>.

<description d'origine verbatim>

---

## Résolution
...
```

Mettre à jour la docstring de la fonction (interrogate/ruff D) en citant le
numéro de ce ken à côté des #605 / #376 existants.

### 2. `src/dashboard/agent_guide.md`

Ajouter la ligne TL;DR en tête du squelette `cat > /tmp/ken-<id>.md`, une 4e
puce à la liste « Preserve the original description verbatim, then add… », et
la répercuter dans le cheatsheet (~l.156).

### 3. `CLAUDE.md` (§ « Working a task off the board », étape 4)

Mentionner le TL;DR en tête de la description de résolution.

### 4. `tests/unit/test_ken.py`

Étendre `test_move_to_review_prints_update_reminder` et
`test_update_status_review_prints_update_reminder` avec
`assert "TL;DR" in result.stderr`. Le test `test_move_to_non_review_no_reminder`
couvre déjà l'absence de rappel hors review.

### 5. Hors repo (meta-repo angel)

`2113.ch/CLAUDE.md` § Tasks (kenboard) duplique le workflow todo→doing→review :
y ajouter la même mention.

## Variante envisagée (non retenue)

Rappel **conditionnel** : la réponse du PATCH renvoie la description complète
(`TaskResponse`, `models/task.py`), on pourrait ne rappeler que si les premières
lignes ne portent pas de marqueur TL;DR — zéro round-trip supplémentaire.
Écarté : les deux rappels existants sont inconditionnels par choix (« cheap
no-op for the agent »), et une détection par regex sur du markdown libre
produirait des faux négatifs. À reconsidérer si le bruit stderr devient gênant.

## Garde-fous

- `pdm run test-unit` (tests des rappels), `pdm run lint`, `pdm run typecheck`.
- interrogate : docstring de `_review_update_reminder` mise à jour.
- Aucun changement de schéma DB ni d'API : le TL;DR est une convention de
  contenu, pas un champ.

---

## Résolution

### Modifications

- `src/dashboard/ken/task_edit.py` — `_review_update_reminder()` : le bloc stderr
  imprimé sur les deux chemins vers review (`ken move --to review` /
  `ken update --status review`) ouvre maintenant sur « Open with a TL;DR line
  (1-2 sentences: problem → what was done) » avant la consigne
  original-verbatim + `## Résolution`. La ligne d'exemple passe de
  `--desc "<original>\n\n---\n\n## Résolution\n..."` à
  `--desc-file <file>   # TL;DR + original + Résolution` — l'ancienne forme était
  précisément celle que `agent_guide.md` déconseille (#393, backslash-n littéral
  en shell double-quoted). Docstring mise à jour (#605, #1091, #393).
- `src/dashboard/agent_guide.md` (servi par `ken help`) — étape 4 réécrite (le
  TL;DR va **au-dessus** de la description d'origine, qui reste verbatim ; motif :
  la carte du board et la page wiki rendue par `ken wiki sync` partagent ce même
  corps) ; ligne TL;DR ajoutée aux deux squelettes (`--desc-file` et heredoc) ;
  récap « Preserve the original description verbatim » → « Open with the TL;DR,
  preserve… » ; cheatsheet passé à `--desc-file`.
- `CLAUDE.md` § « Working a task off the board », étape 4 — même consigne
  (TL;DR + `--desc-file`).
- `tests/unit/test_ken.py` — `test_move_to_review_prints_update_reminder` et
  `test_update_status_review_prints_update_reminder` asservissent `"TL;DR"` sur
  stderr ; `test_move_to_non_review_no_reminder` vérifie l'absence du nudge hors
  review.

### Comportements obtenus

- Tout passage en review imprime la consigne TL;DR au moment exact où l'agent
  s'apprête à rédiger sa description finale — même bloc stderr que le rappel
  résolution (pas de 3ᵉ paragraphe : deux rappels restent affichés, résolution
  et groom).
- Le rappel ne suggère plus une syntaxe cassée : `--desc-file` est cohérent avec
  le guide et avec `ken add`/`ken update --desc-file` (#393).
- Un TL;DR en tête de description profite au board **et** au wiki publié, les
  deux rendant le même corps markdown (`ken wiki sync` → `wiki_detail.py`).
- Cette description elle-même applique la convention (dogfood).

### Garde-fous

- `pdm run test-unit` : 651 passed.
- `pdm run lint` (ruff) : All checks passed. `pdm run typecheck` (mypy) : 65 files,
  no issues. `pdm run flake8` : clean. `pdm run interrogate` : 100 % (min 95).
- `pdm run isort` / `docformatter` / `black` : appliqués, arbre formaté.
- `sh publish.sh` : gate qualité complète + e2e + metrics-gate + Sonar avant
  release PyPI.
- Aucune migration ni changement d'API : le TL;DR est une convention de contenu,
  pas un champ.

### Variante écartée

Rappel conditionnel (ne nudger que si la description ne porte pas déjà un
marqueur TL;DR — la réponse du PATCH renvoie la description, donc sans
round-trip supplémentaire) : écarté pour rester cohérent avec les deux rappels
existants, inconditionnels par choix (« cheap no-op for the agent »), et parce
qu'un regex sur du markdown libre produirait des faux négatifs. À reconsidérer
si le bruit stderr devient gênant.
---

[← retour à cli/ken](index.md) · [voir log](../../log/2026-09-04.md)
