---
id: 44
title: "SEC / FIX / Rate limiting sur /login"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:17
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #44 — SEC / FIX / Rate limiting sur /login

**Sévérité: HIGH**

Aucun rate limit sur `POST /login`. 20 tentatives avec mauvais mot de passe passent en ~30ms chacune. Permet brute force et credential stuffing à grande échelle. Argon2 ralentit naturellement la vérification quand le user existe, mais ce n'est pas un rate-limit.

**Reproduction:** `python pentest/brute_force.py`

**Remédiation:** ajouter `flask-limiter` avec une limite par IP sur `/login` (ex: 5 / minute, 20 / heure). Stocker l'état dans Redis ou en mémoire selon le déploiement. Logger les bursts via structlog (`auth.brute_force_attempt`).
---

[← retour à backend/auth](index.md) · [voir log](../../log.md)
