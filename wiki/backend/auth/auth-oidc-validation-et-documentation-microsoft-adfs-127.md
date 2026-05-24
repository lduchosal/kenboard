---
id: 127
title: "AUTH / OIDC / Validation et documentation Microsoft ADFS"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:26
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #127 — AUTH / OIDC / Validation et documentation Microsoft ADFS

Valider que l'implémentation OIDC de la tâche #126 fonctionne effectivement contre **Microsoft ADFS** (Active Directory Federation Services), qui est le fournisseur d'authentification cible en première intention. Produire la doc de bout en bout pour qu'un opérateur (ou Claude) puisse brancher kenboard sur un ADFS existant.

## Pourquoi ADFS

- C'est le SSO en place sur le réseau cible.
- Permet de réutiliser les comptes AD existants sans gérer un IdP séparé.
- ADFS supporte OIDC depuis ADFS 4.0 (Windows Server 2016+).

## Dépendance

Bloquée par **#126** (l'implémentation Authlib doit être en place). Cette tâche est la **phase de validation + doc** spécifique au provider, pas une réimplémentation.

## Spécificités ADFS à valider

ADFS n'est pas un IdP OIDC "comme les autres" — ses écarts par rapport à Google/Authentik sont documentés et c'est exactement ce que cette tâche doit vérifier :

1. **Discovery URL** : `https://<adfs-host>/adfs/.well-known/openid-configuration` (le préfixe `/adfs` est obligatoire, contrairement aux IdP cloud).
2. **Authority** : `https://<adfs-host>/adfs` (et non la racine).
3. **Claim email manquant ou nommé différemment** : par défaut ADFS n'émet **pas** de claim `email` ni `email_verified`. Le sub est souvent `upn` (`user@domain.local`) et l'email réel doit être ajouté via une **Issuance Transform Rule** dans la console ADFS. À documenter explicitement, sinon la lazy-create de #126 pétera sur `KeyError: 'email'`.
4. **`email_verified` jamais positionné** : ADFS ne le gère pas. Le check `token['userinfo']['email_verified']` de #126 doit donc avoir un mode "trust IdP" : ajouter une variable `OIDC_REQUIRE_EMAIL_VERIFIED` (défaut `true`, mettre à `false` pour ADFS).
5. **Signature `id_token`** : ADFS signe en RS256 par défaut, JWKS publié sur `/adfs/discovery/keys`. Vérifier qu'Authlib le récupère bien via le discovery.
6. **PKCE** : supporté à partir d'ADFS 2019. Si la cible est 2016, désactiver PKCE (variable `OIDC_PKCE`, défaut `true`).
7. **Clock skew** : les serveurs ADFS sont sensibles à l'horloge. Le leeway de 120s d'Authlib devrait suffire mais à valider.
8. **Logout** : ADFS expose `/adfs/oauth2/logout`. Hors scope #126, mentionner dans la doc comme évolution future.
9. **CORS / Referer** : ADFS rejette les redirect_uri non whitelistés au caractère près (slash final, http vs https). À documenter avec un exemple exact.

## Étapes

1. **Côté ADFS** (à exécuter dans un environnement de test, via la console MMC ADFS ou PowerShell) :
   - Créer une **Application Group** "kenboard".
   - Ajouter une **Server application** : prendre note du `client_id` (GUID), définir le redirect URI `https://kenboard.<domaine>/oidc/callback`, générer un **client secret** (tab "Generate a shared secret").
   - Ajouter une **Web API** liée à l'app : identifier = même valeur que client_id, ajouter les scopes `openid`, `email`, `profile`.
   - **Issuance Transform Rules** sur la Web API : ajouter une règle "Send LDAP Attributes as Claims" qui mappe `E-Mail-Addresses` → `email` et `Display-Name` → `name`. Documenter le script PowerShell équivalent (`Set-AdfsApplicationGroup` / `Add-AdfsClientCertificate`).
2. **Côté kenboard** :
   - Renseigner dans `.env` :
     ```
     OIDC_DISCOVERY_URL=https://adfs.example.local/adfs/.well-known/openid-configuration
     OIDC_CLIENT_ID=<guid>
     OIDC_CLIENT_SECRET=<secret>
     OIDC_ALLOWED_EMAIL_DOMAIN=example.local
     OIDC_REQUIRE_EMAIL_VERIFIED=false
     ```
   - Si #126 n'a pas anticipé `OIDC_REQUIRE_EMAIL_VERIFIED`, **rouvrir #126** pour ajouter la variable. C'est probablement le seul ajustement de code nécessaire.
3. **Validation manuelle (smoke test)** :
   - Démarrer kenboard contre l'ADFS de test.
   - Click sur le bouton "Sign in with OIDC" → vérifier la redirection vers la page de login ADFS.
   - Login avec un compte AD existant → vérifier le retour sur `/oidc/callback` puis sur `/`.
   - Vérifier dans la table `users` que la row a bien été créée (lazy-create) avec le bon email.
   - Logout → vérifier que `session_nonce` a tourné et que recharger `/` redirige vers `/login`.
4. **Validation des cas d'erreur** :
   - Compte AD valide mais hors `OIDC_ALLOWED_EMAIL_DOMAIN` → 403 propre.
   - Discovery URL injoignable → message d'erreur explicite, le password local continue de marcher.
   - Client secret invalide → 401 propre côté callback.
   - Horloge serveur décalée de plus de 120s → vérifier le message d'erreur Authlib.
5. **Documentation** — créer **`doc/oidc-adfs.md`** avec :
   - Prérequis ADFS (version, rôle installé, certificat TLS valide).
   - Les **commandes PowerShell exactes** pour créer l'Application Group et les Issuance Transform Rules (préférable aux captures d'écran de la MMC qui datent).
   - Le bloc `.env` minimal pour kenboard.
   - La checklist de smoke test ci-dessus, transformée en runbook.
   - Une section **Troubleshooting** qui couvre au minimum :
     - `KeyError: 'email'` dans le callback → règle d'issuance manquante côté ADFS.
     - `MismatchingStateError` → cookie SameSite ou redirect_uri qui ne match pas au caractère près.
     - `Invalid signature` → JWKS pas récupéré, vérifier l'accès réseau `/adfs/discovery/keys`.
     - `Token expired` → clock skew, synchroniser NTP des deux côtés.
   - Lien retour vers `doc/auth-user.md`.
6. **Mise à jour de `INSTALL.md`** — ajouter ADFS comme premier exemple dans la section OIDC créée par #126, avec un pointeur vers `doc/oidc-adfs.md` pour le détail.
7. **Optionnel — test d'intégration** : si on a accès à un ADFS de lab joignable depuis le poste, écrire un test `tests/e2e/test_oidc_adfs.py` qui n'est exécuté que si `OIDC_ADFS_TEST_URL` est défini dans l'env (skipif sinon). Ce test reste hors de `pdm run test` standard.

## Acceptation

- Smoke test manuel passé contre un ADFS réel (Q ou un humain valide).
- `doc/oidc-adfs.md` existe, contient le PowerShell de provisioning, le `.env` minimal, le runbook de validation et la section troubleshooting.
- Si un ajustement de code dans #126 a été nécessaire (`OIDC_REQUIRE_EMAIL_VERIFIED` ou autre), le documenter dans la résolution de cette tâche **et** rouvrir #126 si elle était déjà mergée.
- `pdm run check` reste vert.

## Hors scope

- Logout côté ADFS (`end_session_endpoint`) : noté dans la doc comme évolution.
- Mapping des groupes AD → `is_admin` : la promotion reste manuelle via `/admin/users`.
- ADFS multi-tenant / multi-relying-party : un seul Application Group suffit pour kenboard.
- Migration depuis WS-Federation ou SAML : kenboard ne supporte que OIDC.

## Référence

- Tâche d'analyse : #125 (review)
- Tâche d'implémentation : #126 (todo) — bloquante
---

[← retour à backend/auth](index.md) · [voir log](../../log.md)
