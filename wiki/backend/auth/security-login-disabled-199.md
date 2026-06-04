---
id: 199
title: "SECURITY / LOGIN_DISABLED"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:46
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #199 — SECURITY / LOGIN_DISABLED

Est-il possible comme en .NET ou en C d'avoir une compilation conditionnelle et le code qui part en prod n'aurait pas l'option LOGIN_DISABLED ? Analyse

---

## Analyse

**Python n'a pas de préprocesseur C/.NET (`#ifdef DEBUG`).** Le code est shippé tel quel, les branches `LOGIN_DISABLED` sont présentes dans le binaire distribué. Options évaluées :

| Option | Verdict |
|---|---|
| 1. Compilation conditionnelle native (`python -O` / `__debug__`) | Rejeté : strip les asserts, docstrings, trop grossier |
| 2. Build-time AST stripping | Rejeté : fragile, dev/prod divergent, deux CI à maintenir |
| 3. Cython / mypyc avec directives | Rejeté : overkill, change l'archi complète |
| 4. Defense-in-depth au démarrage ⭐ | **Retenu** : 15 lignes, double-flag, fail-fast |
| 5. Refactor vers monkeypatch | Reporté : gros refactor, pas prioritaire |
| 6. Test invariant ⭐ | **Retenu** : tripwire statique, prévient les régressions |

## Résolution

### Modifications (options 4 + 6)

**Runtime guard centralisé**
- `src/dashboard/auth_user.py` — nouveau `_is_login_disabled()` qui remplace les 8 lectures directes de `LOGIN_DISABLED`. Raise `RuntimeError` si le flag est set SANS `Config.DEBUG=True`. Log `login_disabled.refused_in_production` pour l'alerting.
- `src/dashboard/auth.py`, `routes/users.py`, `routes/categories.py`, `routes/projects.py`, `routes/pages.py` — tous migrés vers le helper. `current_app` retiré des imports quand devenu inutile.

**Startup guard (défense périmètre)**
- `src/dashboard/app.py` — `create_app()` raise `RuntimeError` si `app.config["LOGIN_DISABLED"]` est set à la fin de la construction avec `DEBUG=False`. L'app refuse de démarrer, aucune requête ne passe.

**Tests d'invariants**
- `tests/unit/test_security_invariants.py` (nouveau) :
  - `test_no_direct_read_outside_helper` — walk AST-free sur `src/dashboard/*.py`, refuse tout `config.get("LOGIN_DISABLED")` hors des 2 fichiers whitelistés (`auth_user.py` = helper, `app.py` = startup check). Whitelist explicite avec justification.
  - `test_helper_is_defined` — vérifie que `_is_login_disabled` existe toujours et lit encore le flag (pas un stub no-op).
  - `test_helper_raises_when_debug_off_and_flag_on` — runtime : `RuntimeError` levée en prod.
  - `test_helper_allows_bypass_in_debug_mode` — runtime : fonctionne normalement en debug.
  - `test_helper_returns_false_when_flag_off` — runtime : False quand flag off.
  - `test_create_app_refuses_login_disabled_without_debug` — startup guard vérifié via `monkeypatch`.

### Comportements obtenus

**Avant** : `LOGIN_DISABLED=True` en prod → auth complètement désactivée, aucune alerte.

**Après (triple protection)** :
1. **Compile-time (statique)** : le test d'invariant refuse tout nouveau chemin de lecture du flag hors du helper. Un dev qui oublie la garde voit le test rouge en CI.
2. **Startup (boot)** : `create_app()` raise si `LOGIN_DISABLED + !DEBUG`. L'app ne démarre pas, gunicorn meurt au boot.
3. **Runtime (requête)** : `_is_login_disabled()` raise si quelqu'un flip le flag à chaud. La première requête qui touche l'auth crashe avec 500 + log `login_disabled.refused_in_production`.

### Garde-fous

- `pdm run test-unit` → 303 passed (6 nouveaux tests #199)
- `pdm run test-integration` → 10 passed
- `pdm run test-e2e` → 53 passed
- `pdm run check` (isort + black + docformatter + mypy + flake8 + interrogate + refurb + lint + vulture + test-quick) → tout vert
---

[← retour à backend/auth](index.md) · [voir log](../../log/2026-05-24.md)
