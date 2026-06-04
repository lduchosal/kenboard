---
id: 344
title: "AUTH / OIDC / Trusted certificate"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:30:01
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #344 — AUTH / OIDC / Trusted certificate

## Demande

Erreur côté kenboard sur `/oidc/login` :
```
SSLError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed:
  unable to get local issuer certificate
host=fs.xx.ch /adfs/.well-known/openid-configuration
```

Le CA self-signed d'ADFS (`xxx-CA.pem`) est installé dans le truststore FreeBSD système (`certctl`), mais Python `requests` / `ssl` ignorent ce truststore et lisent le bundle `certifi` du venv → le CA xx n'y est pas.

---

## Résolution

### Modifications

- `pyproject.toml` : nouvelle **optional extra** `[oidc]` avec `pip-system-certs>=4.0`. Installer kenboard avec `pip install \"kenboard[oidc]\"` patche `requests` + `ssl` au démarrage pour utiliser le truststore OS.
- `doc/oidc-adfs.md` : nouvelle section *Alternative recommandée : extra `[oidc]`* dans le troubleshooting `SSLCertVerificationError`. Explique l'usage + pourquoi c'est un extra.

### Pourquoi un extra et pas une dépendance par défaut

Tentative initiale : `pip-system-certs` ajouté aux `dependencies` runtime → `pdm update` en local plante avec :

```
RecursionError: maximum recursion depth exceeded
  ssl.SSLContext.verify_mode setter recurses indefinitely
  truststore._set_ssl_context_verify_mode → _original_super_SSLContext...
```

Cause : `pdm` lui-même dépend de `truststore` pour son propre client HTTP de résolution. Quand `pip-system-certs` est dans l'env, il re-patche `ssl.SSLContext` via le même `truststore`, et la chaîne de descriptors `verify_mode` boucle sur elle-même.

Sur le serveur de prod FreeBSD, `pdm` n'est PAS installé → pas de conflit. Mais en dev / CI / publish gate, `pdm` est présent → on ne peut pas mettre `pip-system-certs` dans les deps par défaut sans casser le tooling.

L'extra `[oidc]` est le compromis : opt-in à l'install, zéro impact sur le dev workflow.

### Usage côté ops

```sh
# Installation kenboard avec patching auto du truststore système
pip install \"kenboard[oidc]\"
# ou, avec gunicorn :
pip install \"kenboard[prod,oidc]\"
```

Sur le serveur FreeBSD, le CA xx ayant été ajouté via `certctl`, l'appel à `https://fs.xx.ch/adfs/.well-known/openid-configuration` réussira au prochain redémarrage de kenboard.

### Vérif post-install

```sh
# Confirme que pip-system-certs est bien chargé au boot du venv kenboard.
python -c \"import sys; print([m for m in sys.modules if 'pip_system_certs' in m])\"
# → ['pip_system_certs', 'pip_system_certs.bootstrap', 'pip_system_certs.wrapt_requests']

# Confirme que requests honore désormais le truststore système.
python -c \"import requests; requests.get(
  'https://fs.xx.ch/adfs/.well-known/openid-configuration'
).raise_for_status(); print('OK')\"
```

### Garde-fous

- `pdm install` : OK (pip-system-certs absent par défaut)
- `pdm run check` : 394 passed (aucune régression)
- `pdm run test-e2e` : 52 passed

### Alternative documentée

Si l'opérateur ne veut pas l'extra (ou hit le bug `pdm`/`truststore` recursion ailleurs), la doc `oidc-adfs.md` couvre toujours :
1. Concat du root CA dans `certifi/cacert.pem` (fragile, écrasé par upgrade certifi)
2. Variable d'env `REQUESTS_CA_BUNDLE=/path/to/ca.pem` (durable)
---

[← retour à backend/auth](index.md) · [voir log](../../log/2026-05-24.md)
