---
id: 130
title: "DOC / INSTALL / Initialisation du user Q"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:37
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: docs
section_title: "Documentation"
---

# #130 — DOC / INSTALL / Initialisation du user Q

Mettre à jour la document pour expliquer comment on configure le mot de passe du user Q
kenboard set-password Q

---

## Résolution

### Modifications

- **INSTALL.md** — nouvelle section **`## 6. Initialiser le mot de passe de l'admin`** insérée entre Migrations et Lancer le serveur. Renumérotation des sections suivantes (Lancer → 7, Tests → 8, Générer pages statiques → 9, Reverse proxy → 10, Vérification → 11).

### Contenu ajouté

- Explique que la migration `0004.create_users.sql` insère 4 users (Q, Alice, Bob, Claire) avec un `password_hash` vide et que sans `set-password` **personne ne peut se loguer** (la web UI refuse les credentials avec hash vide).
- Commande exacte : `kenboard set-password Q`.
- Sortie attendue (prompt double + confirmation), contrainte ≥ 8 caractères, hash argon2.
- Note que la même commande sert plus tard pour réinitialiser un autre user ou changer son propre mot de passe en CLI.
- Note de troubleshooting : si `User Q not found`, repasser par l'étape 5 (migrations).
- Section "Lancer le serveur" complétée d'une ligne pour rappeler que le login se fait avec Q + le mot de passe défini à l'étape 6.

### Pourquoi cette position dans le doc

L'enchaînement naturel est : créer la DB → migrer → seed users (vide) → **set-password** → démarrer le serveur. Insérer la section avant "Lancer le serveur" évite qu'un opérateur fraîchement installé démarre l'app puis se retrouve bloqué à la page de login sans comprendre pourquoi.

### Garde-fous

- Pas de modification de code, uniquement du markdown.
- Renumérotation des ancres : aucune autre page du repo ne pointe vers `INSTALL.md#6-...` (vérifié — il n'y a pas de lien interne vers ces ancres).
- Aucun gate à rejouer (`pdm run check` non pertinent pour une modif doc seule).

### Hors scope

- `KENBOARD_SECRET_KEY` n'est toujours pas mentionné dans la section 4 (Configuration) de `INSTALL.md` alors qu'il est obligatoire en prod (`DEBUG=false`). À traiter dans une tâche dédiée si ça gêne.
- La doc `README.md` n'a pas été touchée.
---

[← retour à docs](index.md) · [voir log](../log/2026-05-24.md)
