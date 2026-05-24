---
id: 234
title: "EMAIL / Format texte et HTML"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:56
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/email
section_title: "Email & notifications"
---

# #234 — EMAIL / Format texte et HTML

Les emails envoyes depuis le systeme doivent etre au format TXT et HTML.

---

## Resolution

### Problemes corriges

1. **Entites HTML** — Les templates utilisaient `&eacute;`, `&mdash;` etc. au lieu de caracteres UTF-8. Remplaces par les vrais caracteres.
2. **Lien invisible** — Ajout du lien en texte brut sous le bouton ('Si le bouton ne fonctionne pas, copiez ce lien...')
3. **Pas de fallback texte** — Ajout de templates .txt pour chaque email
4. **Multipart** — email.py envoie maintenant text/plain + text/html (RFC 2046)

### Modifications

- `src/dashboard/email.py` — Envoie multipart (text + HTML). Derive automatiquement le template .txt depuis le .html.
- `src/dashboard/templates/email/password_reset.html` — Caracteres UTF-8, lien en clair ajoute
- `src/dashboard/templates/email/password_reset.txt` (nouveau) — Version texte
- `src/dashboard/templates/email/verify_email.html` — Caracteres UTF-8, lien en clair ajoute
- `src/dashboard/templates/email/verify_email.txt` (nouveau) — Version texte

### Garde-fous

- pytest unit : 343 passed
- mypy : clean
- flake8 : clean
---

[← retour à backend/email](index.md) · [voir log](../../log.md)
