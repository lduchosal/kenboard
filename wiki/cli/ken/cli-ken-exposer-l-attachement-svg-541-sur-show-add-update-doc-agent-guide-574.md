---
id: 574
title: "CLI / ken — exposer l'attachement SVG (#541) sur show/add/update + doc agent_guide"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-30T23:31:37
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: cli/ken
section_title: "ken task CLI"
---

# #574 — CLI / ken — exposer l'attachement SVG (#541) sur show/add/update + doc agent_guide

L'extension paintbrush peuple tasks.attachement avec un SVG (#541). La CLI 'ken' ignorait complètement ce champ.

---

## Résolution

### Modifications
- src/dashboard/ken.py :
  - Helper `_read_attachement_file(path)` : lit un SVG depuis un fichier, vérifie la taille avant POST (cap MEDIUMTEXT 16 MB), UsageError clair si oversize ou unreadable.
  - `ken show <id>` : nouvelle option `--save-attachement PATH` qui écrit le SVG du champ dans le fichier indiqué (+ confirmation stderr). Sans le flag, affiche un hint `attachement : 145.2 KB SVG (use ...)` après les autres champs si l'attachement est non-vide. **Ne dump jamais le SVG brut sur stdout** (flood terminal).
  - `ken add` : nouvelle option `--attachement-file PATH` qui ajoute le contenu au body POST.
  - `ken update` : nouvelle option `--attachement-file PATH` qui ajoute attachement au PATCH body. Le garde 'nothing to update' inclut maintenant l'option.
- src/dashboard/agent_guide.md : nouvelle section 'Attachements (SVG paintbrush)' avec les 4 idiomes (add, update, show, show --save) + note sur le cap MEDIUMTEXT + workflow agent (save → relire → reformuler titre+desc).
- onboarding.py inchangé (déjà oriente vers `ken help` qui imprime agent_guide.md).
- tests/unit/test_ken.py — 5 régressions :
  - add avec --attachement-file → SVG dans body POST.
  - update avec --attachement-file → SVG dans body PATCH.
  - --attachement-file oversize → UsageError client (cap monkeypatché pour rapidité).
  - show affiche le hint + ne dump pas le SVG brut.
  - show --save-attachement écrit le fichier.

### Garde-fous
- mypy ken.py : clean.
- TestCliMutations : 58/58 passed (52 existants + 6 nouveaux Phase #574).
- ken add/show/update --help affichent bien les nouvelles options.
---

[← retour à cli/ken](index.md) · [voir log](../../log/2026-05-30.md)
