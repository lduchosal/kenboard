---
id: 254
title: "UX / Authentification / Changement d'IP"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:48
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #254 — UX / Authentification / Changement d'IP

## Demande

Lors d'un changement d'IP (roaming WiFi→4G, etc.), le kenboard demande à se réauthentifier. C'est embêtant quand on crée ou que l'on edit une tâche, le travail est perdu.

---

## Diagnostic

`auth_user.py:69` configure `flask_login.LoginManager.session_protection = \"strong\"`. Flask-Login hashe (User-Agent + remote IP) au login et le stocke dans la session ; le mode `strong` **supprime la session et déconnecte l'utilisateur** au moindre mismatch. C'est exactement ce qui se passe lors d'un roaming réseau.

## Décision : Option 3 — override de l'identifier pour ne hasher que le User-Agent

Validé par l'utilisateur. Modifie `LoginManager.session_identifier_generator` pour ne hasher que le User-Agent, en laissant tomber le composant IP. Conserve la protection \"cookie utilisé depuis un autre navigateur\" (UA différent) mais tolère \"même navigateur, réseau différent\" (cas légitime quotidien).

### Pourquoi le check IP coûte plus en UX qu'il n'apporte en sécurité

- Network-level MitM du cookie : faiblement protégé par cette mesure post-HTTPS+HSTS. Là où ça pourrait arriver (CA compromis, WiFi hostile sans HSTS preload), on a déjà perdu.
- Vol de cookie device-to-device (XSS, exfiltration filesystem) : l'IP n'aide pas — l'IP de l'attaquant est juste *différente*, signal indistinguable du roaming légitime. Couvert par `session_nonce` (déjà en place, rotation au logout / changement de mot de passe).

Le check IP est principalement un coût UX sans gain de sécurité réel par rapport aux protections existantes.

## Plan d'implémentation

1. Ajouter `_ua_only_session_identifier()` dans `auth_user.py` qui hashe SHA-512 du seul `User-Agent`.
2. Bind sur le `LoginManager` : `login_manager.session_identifier_generator = _ua_only_session_identifier`.
3. Test unitaire : deux requêtes même UA + IP différente → même hash.
4. Test intégration : login depuis IP A, requête depuis IP B → session conservée.

## Pistes connexes (orthogonales, pas dans ce ticket)

- **Autosave du modal de tâche dans localStorage** pendant la frappe : couvre les autres scénarios de perte de session (logout, expiry cookie, change password). Ticket séparé si besoin.
---

[← retour à backend/auth](index.md) · [voir log](../../log.md)
