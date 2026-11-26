# Scorecard des dépendances runtime

<!-- Généré par scripts/dep_scorecard.py depuis doc/dep-scorecard.csv — ne pas éditer (ken #1242). -->

Snapshot **2026-11-26T15:56Z** — 36 paquets de `kenboard[prod,oidc]`, score médian **6.6**, 4 sous 5, 4 sans scorecard, 24 avec attestation PyPI.

## Divergences

Snapshot 2026-11-26T15:56Z vs 2026-11-26T14:37Z :

- deprecated left the runtime closure
- flask-limiter left the runtime closure
- limits left the runtime closure
- ordered-set left the runtime closure
- packaging left the runtime closure
- wrapt left the runtime closure

## État

| Paquet | Version | Score | Maintained | Code-Review | Dangerous-Workflow | Signed-Releases | Attestation | Scorecard du | Repo |
|---|---|---|---|---|---|---|---|---|---|
| authlib | 1.9.10 | — |  |  |  |  | yes |  | github.com/authlib/authlib |
| blinker | 1.9.0 | — |  |  |  |  | yes |  | github.com/pallets-eco/blinker |
| joserfc | 1.8.0 | — |  |  |  |  | yes |  | github.com/authlib/joserfc |
| typing-inspection | 0.4.5 | — |  |  |  |  | yes |  | github.com/pydantic/typing-inspection |
| flask-login | 0.6.3 | 3.2 | 0 | 1 | 10 | -1 | no | 2026-11-16 | github.com/maxcountryman/flask-login |
| zxcvbn | 4.5.0 | 3.5 | 0 | 7 | 10 | -1 | no | 2026-11-23 | github.com/dwolfhub/zxcvbn-python |
| aiosql | 16.2 | 4.2 | 10 | 0 | 10 | -1 | no | 2026-11-23 | github.com/nackjicholson/aiosql |
| flask-cors | 6.0.5 | 4.4 | 0 | 4 | 10 | -1 | yes | 2026-11-23 | github.com/corydolphin/flask-cors |
| cffi | 2.1.1 | 5.0 | 10 | 8 | 10 | -1 | no | 2026-11-23 | github.com/python-cffi/cffi |
| pyyaml | 6.0.4 | 5.1 | 2 | 2 | 10 | -1 | no | 2026-11-16 | github.com/yaml/pyyaml |
| annotated-types | 0.8.0 | 5.2 | 9 | 9 | 10 | -1 | no | 2026-11-23 | github.com/annotated-types/annotated-types |
| itsdangerous | 2.2.0 | 5.4 | 0 | 0 | 10 | 10 | no | 2026-11-23 | github.com/pallets/itsdangerous |
| gunicorn | 27.0.1 | 5.5 | 10 | 0 | 10 | 0 | no | 2026-11-23 | github.com/benoitc/gunicorn |
| markdown | 3.11.4 | 5.5 | 10 | 7 | 10 | 0 | no | 2026-08-24 (deps.dev, ancien) | github.com/python-markdown/markdown |
| pip-system-certs | 5.3 | 5.9 | 10 | 1 |  | -1 | no | 2023-11-20 (ancien) | gitlab.com/alelec/pip-system-certs |
| jinja2 | 3.1.6 | 6.0 | 6 | 0 | 10 | 10 | yes | 2026-11-23 | github.com/pallets/jinja |
| werkzeug | 3.1.9 | 6.0 | 10 | 0 | 10 | 0 | yes | 2026-11-16 | github.com/pallets/werkzeug |
| pip | 26.3 | 6.2 | 10 | 3 | 10 | -1 | yes | 2026-11-02 | github.com/pypa/pip |
| pycparser | 3.12 | 6.2 | 10 | 1 | 10 | -1 | no | 2026-11-23 | github.com/eliben/pycparser |
| python-dotenv | 1.2.4 | 6.5 | 10 | 5 | 10 | -1 | yes | 2026-11-09 | github.com/theskumar/python-dotenv |
| certifi | 2026.11.20 | 6.7 | 10 | 6 | 10 | -1 | yes | 2026-11-23 | github.com/certifi/python-certifi |
| pydantic | 2.14.4 | 6.9 | 10 | 6 | 10 | -1 | yes | 2026-11-23 | github.com/pydantic/pydantic |
| pydantic-core | 2.50.5 | 6.9 | 10 | 6 | 10 | -1 | no | 2026-11-23 | github.com/pydantic/pydantic |
| pymysql | 1.2.4 | 7.0 | 10 | 1 | 10 | -1 | yes | 2026-08-24 (deps.dev, ancien) | github.com/pymysql/pymysql |
| flask | 3.1.3 | 7.1 | 10 | 0 | 10 | 6 | yes | 2026-11-23 | github.com/pallets/flask |
| click | 8.5.1 | 7.3 | 10 | 8 | 10 | 0 | yes | 2026-11-23 | github.com/pallets/click |
| markupsafe | 3.0.4 | 7.3 | 10 | 2 | 10 | 6 | yes | 2026-11-23 | github.com/pallets/markupsafe |
| requests | 2.34.2 | 7.8 | 4 | 10 | 10 | 0 | yes | 2026-11-23 | github.com/psf/requests |
| argon2-cffi | 25.1.0 | 7.9 | 10 | 0 | 10 | -1 | yes | 2026-10-26 | github.com/hynek/argon2-cffi |
| argon2-cffi-bindings | 26.2.0 | 8.1 | 10 | 2 | 10 | -1 | yes | 2026-10-26 | github.com/hynek/argon2-cffi-bindings |
| structlog | 26.1.0 | 8.1 | 10 | 2 | 10 | -1 | yes | 2026-11-23 | github.com/hynek/structlog |
| cryptography | 50.0.2 | 8.5 | 10 | 10 | 10 | -1 | yes | 2026-11-23 | github.com/pyca/cryptography |
| idna | 3.20 | 8.6 | 10 | 3 | 10 | 8 | yes | 2026-11-26 | github.com/kjd/idna |
| urllib3 | 2.8.0 | 8.6 | 10 | 8 | 10 | 0 | yes | 2026-11-25 | github.com/urllib3/urllib3 |
| typing-extensions | 4.16.0 | 8.7 | 10 | 10 | 10 | -1 | yes | 2026-11-23 | github.com/python/typing_extensions |
| charset-normalizer | 3.5.3 | 9.0 | 10 | 3 | 10 | 10 | yes | 2026-11-24 | github.com/jawah/charset_normalizer |

## Angles morts

Aucun scorecard (ni OpenSSF ni deps.dev) : rien ne mesure ces projets, à surveiller d'autant plus s'ils sont sensibles.

- authlib 1.9.10 — github.com/authlib/authlib, attestation PyPI
- blinker 1.9.0 — github.com/pallets-eco/blinker, attestation PyPI
- joserfc 1.8.0 — github.com/authlib/joserfc, attestation PyPI
- typing-inspection 0.4.5 — github.com/pydantic/typing-inspection, attestation PyPI
