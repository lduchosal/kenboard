---
id: 548
title: "EXTENSION / paintbrush - phase 7 cleanup #520"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-31T00:01:33
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: extension
section_title: "Browser extension"
---

# #548 — EXTENSION / paintbrush - phase 7 cleanup #520

Retirer dom-anchor-text-quote, dom-anchor-text-position des deps. Supprimer le code quote-mode : selection adder, anchor reapply, storage kb_anno:, drawer ancien, etc. Mettre à jour /aide section 5 (paintbrush au lieu d'Alt+K). README extension. (Epic #541)

---

## Annulée — fusionnée avec #549

Le code quote-mode est déjà supprimé (la réécriture complète d'annotate.src.js en mode paintbrush a remplacé tout l'ancien contenu, le bundle est passé de 113 KB à 27 KB → 30 KB sans les libs d'ancrage).

Reste à faire : `npm uninstall dom-anchor-text-{quote,position}` + /aide section 5 + README extension. Ces 3 items sont consolidés dans **#549** qui regroupe désormais tout le cleanup + tests.
---

[← retour à extension](index.md) · [voir log](../log.md)
