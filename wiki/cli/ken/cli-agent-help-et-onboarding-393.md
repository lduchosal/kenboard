---
id: 393
title: "CLI / AGENT / help et onboarding"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:30:08
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: cli/ken
section_title: "ken task CLI"
---

# #393 — CLI / AGENT / help et onboarding

## Demande

Les agents envoient parfois une description au format MD, mais ça s'affiche cassé (newlines manquants, MD broken). Améliorer le ken CLI et / ou la doc agent. Suggestion : `ken add --file body.md`.

---

## Diagnostic

`src/dashboard/agent_guide.md` ligne 30 montrait `--desc "...\\n..."` aux agents. En bash, `\\n` dans un double-quoted string n'est **pas** interprété comme un newline — c'est stocké littéralement comme 2 caractères. Conséquence : la description côté serveur contient des `\\n` littéraux qui cassent le rendu markdown. Les agents qui suivaient le guide produisaient des descriptions cassées.

## Résolution

### CLI (`src/dashboard/ken.py`)

Trois idioms supportés, par ordre de robustesse :

1. `--desc-file PATH` ⭐ **recommandé** : lit le body depuis un fichier disque. Zéro escape shell, marche sur tout host d'agent capable d'écrire un fichier temporaire.
2. `--desc -` : lit depuis stdin (heredoc-friendly).
3. `--desc \"text\"` : littéral inchangé (single-line uniquement).

Helper `_resolve_desc(desc, desc_file)` :
- `--desc-file` set → lit le fichier (`UsageError` si `--desc` ET `--desc-file` sont passés simultanément).
- `--desc -` → lit `sys.stdin`.
- Sinon → passe-through.

`add` et `update` exposent les deux options. Help text + docstrings (raw strings pour flake8 D301) mentionnent le piège `\\n` et renvoient à `ken help`.

### Doc agent (`src/dashboard/agent_guide.md`)

Section *Passing multi-line markdown safely* refondue :
- ⚠️ explicite sur `--desc \"...\\n...\"` qui casse tout.
- **Best practice** mise en avant : `--desc-file /tmp/ken-<id>.md` (2 étapes : `cat > file <<EOF`, puis `ken update <id> --desc-file file`).
- Alternatives B (heredoc dans `\$(cat <<EOF...)`) et C (`--desc -` + stdin).
- Note sur l'ANSI-C quoting `\$'...\\n...'` pour 2-3 lignes max.
- \"Passing both --desc and --desc-file is an error — pick one.\"

### Tests (`tests/unit/test_ken.py`, +7 dans `TestCliMutations`)

1. `ken add T --desc -` lit stdin
2. `ken update <id> --desc -` lit stdin
3. `ken add T --desc \"literal\"` passe-through unchanged
4. `ken add T --desc-file body.md` lit le fichier
5. `ken update <id> --desc-file body.md` lit le fichier
6. `--desc` + `--desc-file` ensemble → UsageError (\"not both\")
7. `--desc-file` sur chemin inexistant → fail fast (Click `Path(readable=True)`)

### Comportements obtenus

- Les agents qui écrivent un fichier temp (la capacité la plus universelle des hosts) ont un chemin sans aucun escape.
- Les agents capables de pipe stdin ont aussi un chemin (`--desc -` + heredoc).
- Les usages legacy `--desc \"single line\"` continuent à marcher.
- L'erreur explicite si on mélange `--desc` + `--desc-file` évite les surprises silencieuses.
- Doc agent met `--desc-file` en avant comme **best practice** pour les agents.

### Garde-fous

- `pdm run check` : 402 passed (395 + 7 nouveaux)
- `pdm run test-e2e` : 52 passed / 0 failed
- mypy / ruff / flake8 / interrogate / vulture : clean
---

[← retour à cli/ken](index.md) · [voir log](../../log/2026-05-24.md)
