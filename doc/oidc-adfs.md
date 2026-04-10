# OIDC avec Microsoft ADFS

Guide pour brancher kenboard sur un serveur **Active Directory Federation
Services** (ADFS) via OpenID Connect. Testé sur ADFS 4.0+ (Windows
Server 2016+).

> Voir aussi : `doc/auth-user.md` section OIDC pour le fonctionnement
> générique du module `auth_oidc.py`.

## Prérequis

- ADFS 4.0+ (Windows Server 2016+) avec le rôle **Federation Service**
  installé.
- Un certificat TLS valide sur l'endpoint ADFS (`https://<adfs-host>/adfs`).
- Accès admin à la console ADFS (MMC) ou PowerShell sur le serveur.
- kenboard >= 0.1.37 avec `authlib` et `requests` installés.

## 1. Côté ADFS — Enregistrer kenboard

### Via PowerShell (recommandé)

```powershell
# 0. Créer l'Application Group (conteneur)
$appGroupName = "kenboard"
$redirectUri   = "https://kenboard.<domaine>/oidc/callback"

New-AdfsApplicationGroup -Name $appGroupName -ApplicationGroupIdentifier $appGroupName

# 1. Générer un Client ID (GUID) puis créer le Server Application
$clientId = [guid]::NewGuid().ToString()

# Server Application (génère un client_secret)
Add-AdfsServerApplication `
    -Name "$appGroupName - Server" `
    -ApplicationGroupIdentifier $appGroupName `
    -Identifier $clientId `
    -RedirectUri $redirectUri `
    -GenerateClientSecret

# Prendre note du Secret affiché → OIDC_CLIENT_SECRET dans .env
# Le $clientId généré plus haut → OIDC_CLIENT_ID dans .env

# Web API (scopes OIDC)
Add-AdfsWebApiApplication `
    -Name "$appGroupName - API" `
    -ApplicationGroupIdentifier $appGroupName `
    -Identifier $clientId

# 2. Autoriser le Server Application à accéder à la Web API
#    Sans ce grant, ADFS retourne "The client is not allowed to access
#    the requested resource" au moment du token exchange.
Grant-AdfsApplicationPermission `
    -ClientRoleIdentifier $clientId `
    -ServerRoleIdentifier $clientId `
    -ScopeNames "openid"

# 3. Autoriser un groupe AD à utiliser l'application
#    Sans cette Issuance Authorization Rule, ADFS refuse l'accès à tous
#    les utilisateurs ("access denied"). Remplacer <NOM_DU_GROUPE> par
#    le groupe AD autorisé (ex: "Domain Users" pour tous, ou un groupe
#    spécifique comme "Kenboard_Users").
$groupName = "<NOM_DU_GROUPE>"
$authzRules = @"
@RuleTemplate = "Authorization"
@RuleName = "Permit $groupName"
exists([Type == "http://schemas.microsoft.com/ws/2008/06/identity/claims/groupsid",
        Value =~ "(?i)$groupName"])
=> issue(Type = "http://schemas.microsoft.com/authorization/claims/permit",
         Value = "true");
"@

# Alternative : autoriser tout le monde (moins restrictif)
# $authzRules = '@RuleTemplate = "AllowAllAuthzRule"
# => issue(Type = "http://schemas.microsoft.com/authorization/claims/permit",
#          Value = "true");'

Set-AdfsWebApiApplication `
    -TargetIdentifier $clientId `
    -IssuanceAuthorizationRules $authzRules

# 4. Issuance Transform Rules — mapper les attributs AD en claims OIDC
#    Sans cette étape, le id_token ne contient PAS de claim `email` ni `name`.
$rules = @"
@RuleTemplate = "LdapClaims"
@RuleName = "LDAP to OIDC claims"
c:[Type == "http://schemas.microsoft.com/ws/2008/06/identity/claims/windowsaccountname",
   Issuer == "AD AUTHORITY"]
=> issue(store = "Active Directory",
   types = ("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname"),
   query = ";mail,displayName;{0}", param = c.Value);
"@

Set-AdfsWebApiApplication `
    -TargetIdentifier $clientId `
    -IssuanceTransformRules $rules
```

### Via la console MMC (alternative)

1. **Application Groups** → New Application Group → "kenboard".
2. Template : **Server application accessing a web API**.
3. **Server Application** :
   - Name : `kenboard - Server`
   - Redirect URI : `https://kenboard.<domaine>/oidc/callback`
   - Copier le **Client Identifier** (GUID)
   - Tab "Credentials" → **Generate a shared secret** → copier le secret
4. **Web API** :
   - Identifier : coller le même GUID que le Client Identifier
   - Tab "Issuance Transform Rules" → Add Rule :
     - Template : **Send LDAP Attributes as Claims**
     - LDAP Store : Active Directory
     - Mappings :
       - `E-Mail-Addresses` → `E-Mail Address`
       - `Display-Name` → `Given Name`
5. Finish.

## 2. Côté kenboard — Configuration `.env`

```env
OIDC_DISCOVERY_URL=https://<adfs-host>/adfs/.well-known/openid-configuration
OIDC_CLIENT_ID=<GUID du Server Application>
OIDC_CLIENT_SECRET=<secret généré>

# ADFS ne renvoie PAS le claim email_verified → désactiver le check
OIDC_REQUIRE_EMAIL_VERIFIED=false

# ADFS n'a pas de scope "email" — utiliser allatclaims pour récupérer
# tous les claims configurés dans les Issuance Transform Rules
OIDC_SCOPES=openid profile allatclaims

# Optionnel : restreindre aux emails du domaine AD
OIDC_ALLOWED_EMAIL_DOMAIN=example.local
```

> **Attention au Discovery URL** : le préfixe `/adfs` est **obligatoire**
> sur ADFS, contrairement aux IdP cloud (Google, Authentik) qui servent
> le discovery à la racine.

### PKCE

- ADFS 2019+ (Windows Server 2019) : PKCE S256 supporté. Kenboard
  l'active par défaut via `code_challenge_method: S256`.
- ADFS 2016 : PKCE **non supporté**. Ajouter dans `.env` :
  ```env
  # TODO: ajouter OIDC_PKCE=false quand kenboard le supporte (#127)
  ```
  En attendant, le flow authorization code fonctionne sans PKCE — c'est
  moins sécurisé mais acceptable sur un réseau interne avec TLS.

## 3. Appliquer la migration

```sh
kenboard migrate
```

La migration `0012` (+ recovery `0013`) ajoute `users.email` à la
table. Sans cette colonne, le callback OIDC crash avec
`Unknown column 'email' in 'field list'`.

## 4. Redémarrer

```sh
service kenboard restart
# ou : kenboard prod (si installé avec [prod])
```

## 5. Smoke test

| Étape | Action | Résultat attendu |
|---|---|---|
| 1 | Ouvrir `https://kenboard.<domaine>/login` | Le bouton "Sign in with OIDC" apparaît sous le formulaire |
| 2 | Cliquer le bouton | Redirection vers la page de login ADFS |
| 3 | Se connecter avec un compte AD | Retour sur kenboard, page kanban affichée |
| 4 | Vérifier en DB | `SELECT name, email, is_admin FROM users WHERE email='<email-AD>';` → row présente, `is_admin=0` |
| 5 | Cliquer Déconnexion | Retour sur `/login`, recharger `/` redirige vers `/login` |
| 6 | Se reconnecter par password (Q) | Fonctionne — les deux méthodes coexistent |

## 6. Troubleshooting

### `KeyError: 'email'` dans le callback

**Cause** : les Issuance Transform Rules ne sont pas configurées côté
ADFS — le `id_token` ne contient pas de claim `email`.

**Fix** : ajouter la règle "Send LDAP Attributes as Claims" qui mappe
`E-Mail-Addresses` → `email` (cf. section 1 ci-dessus).

Vérifier depuis le serveur kenboard :

```sh
curl -s "https://<adfs-host>/adfs/.well-known/openid-configuration" | python3 -m json.tool | grep claims
```

Si `claims_supported` ne liste pas `email`, les Issuance Rules ne sont
pas en place.

### `The client is not allowed to access the requested resource`

**Cause** : le `Grant-AdfsApplicationPermission` n'a pas été exécuté,
ou le scope demandé (`email`, `allatclaims`) n'est pas reconnu par
cette version d'ADFS (MSIS9605/MSIS9622).

**Fix** : exécuter le Grant avec le scope minimal `openid` :

```powershell
Grant-AdfsApplicationPermission `
    -ClientRoleIdentifier $clientId `
    -ServerRoleIdentifier $clientId `
    -ScopeNames "openid"
```

### `Access denied` après authentification réussie

**Cause** : pas d'Issuance Authorization Rule sur la Web API. ADFS
refuse l'accès par défaut si aucune règle n'autorise les utilisateurs.

**Fix** : ajouter une règle d'autorisation (cf. étape 3 du provisioning
PowerShell). Pour autoriser tout le monde en urgence :

```powershell
$authzRules = '@RuleTemplate = "AllowAllAuthzRule"
=> issue(Type = "http://schemas.microsoft.com/authorization/claims/permit",
         Value = "true");'
Set-AdfsWebApiApplication -TargetIdentifier $clientId -IssuanceAuthorizationRules $authzRules
```

### `MismatchingStateError` ou `state parameter mismatch`

**Cause** : le `redirect_uri` enregistré côté ADFS ne correspond pas
**au caractère près** à celui que kenboard envoie.

**Fix** : vérifier que le redirect URI dans l'Application Group est
exactement `https://kenboard.<domaine>/oidc/callback` — pas de slash
final, pas de `http` au lieu de `https`, pas de port explicite si le
reverse proxy est sur 443.

### `Invalid signature` ou `JWK not found`

**Cause** : Authlib ne peut pas récupérer les clés de signature ADFS
à `https://<adfs-host>/adfs/discovery/keys`.

**Fix** :
- Vérifier que le serveur kenboard peut joindre le serveur ADFS :
  `curl -s https://<adfs-host>/adfs/discovery/keys`
- Vérifier que le certificat TLS ADFS est valide (pas auto-signé, ou
  ajouté au trust store Python)

### `Token expired` / `token is not valid yet`

**Cause** : décalage d'horloge (clock skew) entre le serveur ADFS et
le serveur kenboard.

**Fix** : synchroniser NTP des deux côtés. Authlib applique un leeway
de 120 secondes — au-delà, le token est rejeté.

```sh
# Sur FreeBSD (web2)
ntpdate pool.ntp.org
```

### Le bouton "Sign in with OIDC" n'apparaît pas

**Cause** : une des trois variables `OIDC_DISCOVERY_URL`,
`OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET` est vide ou absente du `.env`.

**Fix** : vérifier le `.env` et redémarrer kenboard.

### `ModuleNotFoundError: No module named 'requests'`

**Cause** : kenboard installé sans `requests` (dépendance transitoire
d'Authlib). Corrigé dans kenboard >= 0.1.37.

**Fix** : `pip install requests` dans le venv, ou mettre à jour kenboard.

## Hors scope (évolutions futures)

- **Logout côté ADFS** : ADFS expose `/adfs/oauth2/logout`. Kenboard
  `/logout` ne détruit que la session locale (rotation `session_nonce`),
  le user reste connecté côté ADFS. Pour un SSO logout complet, il
  faudrait rediriger vers `end_session_endpoint` (à implémenter dans
  `auth_oidc.py`).
- **Mapping groupes AD → `is_admin`** : un claim `groups` pourrait
  être mappé via les Issuance Transform Rules. Kenboard ne le lit pas
  encore — la promotion admin reste manuelle via `/admin/users`.
- **Multi-tenant / multi-relying-party** : un seul Application Group
  suffit pour une instance kenboard.
