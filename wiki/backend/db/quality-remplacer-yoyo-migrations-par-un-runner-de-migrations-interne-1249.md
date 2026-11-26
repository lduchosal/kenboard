---
id: 1249
title: "QUALITY / Remplacer yoyo-migrations par un runner de migrations interne"
status: done
who: "Claude"
due_date: 
updated_at: 2026-11-26T16:23:43
classified_at: 2026-11-26T15:38:32
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/db
section_title: "Database (SQL + migrations)"
---

# #1249 — QUALITY / Remplacer yoyo-migrations par un runner de migrations interne

**TL;DR** — yoyo-migrations était un angle mort supply-chain (ni scorecard ni attestation, 3 transitifs). Il exécutait aussi nos blocs `-- rollback` en aller, ce qui est la vraie cause des incidents 0008, 0010 et 0012, et il recevait le mot de passe DDL en argv → remplacé par un runner forward-only interne (`src/dashboard/migrate.py`, PyMySQL seul), compatible avec la table `_yoyo_migration`. Le schéma produit est identique, les bases existantes ne rejouent rien, et 6 paquets sortent de la closure runtime.

Suite de #1242 (scoreboard `doc/dep-scorecard.md`). `yoyo-migrations` a le pire profil supply-chain de la closure runtime, et c'est le paquet qui tourne avec les credentials DDL.

## Constat

- **yoyo-migrations 9.0.0** : dernière release 2024-08-10, hébergé sur sourcehut (ollycope.com) → deps.dev ne connaît aucun repo source, **aucun scorecard OpenSSF, aucune attestation PyPI**. Angle mort complet du scoreboard.
- Tire 3 transitifs : `tabulate` (Maintained 0, score 4.0), `sqlparse` (5.4), `importlib-metadata`.
- Exécuté par `kenboard migrate` / `migrate-test` (`src/dashboard/cli.py:105-130`, `:213`) avec `DB_MIGRATE_USER` = `dashboard_admin` (DDL).
- **Bug connu** : son parseur SQL ne coupe pas toujours au marqueur `-- rollback` et exécute le fichier entier en aller → règle 5 de `CLAUDE.md` (rollback obligatoirement no-op `SELECT 1`), cause de la casse de 0012 (`DROP COLUMN email` exécuté pendant l'apply). Deux autres incidents (0008→0009, 0010→0011) : migration enregistrée appliquée alors que le DDL n'a pas persisté.
- **Fuite de credentials** : `cli.py` construit `mysql://user:PASSWORD@host/db` et le passe en **argv** au binaire `yoyo` → mot de passe DDL visible dans `ps` / `/proc` par tout utilisateur local de l'hôte pendant la migration.

## Proposition

Runner de migrations interne (~100-150 lignes, `src/dashboard/migrate.py`), PyMySQL seulement :

- Lit `src/dashboard/migrations/*.sql` triés par nom ; ignore le bloc après `-- rollback` (jamais exécuté — on n'a pas de rollback réel, cf. règle 5) ; découpe les statements de façon explicite (pas de parseur heuristique) — à définir : délimiteur `;` en fin de ligne, en respectant les blocs `PREPARE`/`EXECUTE` des migrations idempotentes existantes.
- **Compatible `_yoyo_migration`** : réutilise la table existante (`migration_hash`, `migration_id`, `applied_at_utc`) pour que les bases déjà migrées en prod ne rejouent rien, et que `about_migrations` (`queries/about.sql`, #1165) continue de fonctionner. Éventuellement `_yoyo_log` en écriture seule.
- `-- depends:` : vérifier que la dépendance est appliquée (ordre lexical suffit aujourd'hui, 22 fichiers linéaires).
- Connexion PyMySQL directe avec les creds de `Config` → plus de mot de passe en argv.
- Verrou (`GET_LOCK`) pour éviter deux `migrate` concurrents.
- Retire `yoyo-migrations` de `pyproject.toml` (+ entrée deptry DEP002), réécrit `tests/unit/test_cli.py::test_migrate_invokes_yoyo_*`, met à jour `CLAUDE.md` § migrations (règle 5 reformulée) et `doc/architecture.md`.

## Critères

- `kenboard migrate` sur une base prod existante = no-op (toutes les migrations déjà dans `_yoyo_migration`).
- Sur base vide : applique 0001→0022, résultat identique au schéma produit par yoyo (diff `SHOW CREATE TABLE`).
- Le bloc `-- rollback` n'est **jamais** exécuté (test unitaire sur un fichier piégé type 0012).
- Le scoreboard perd 4 lignes (yoyo, tabulate, sqlparse, importlib-metadata si plus requis) ; GuardDog + scorecard verts.


## Résolution

### Découverte : la vraie cause racine des incidents 0008, 0010 et 0012

yoyo **ne connaît pas** de marqueur `-- rollback` dans un fichier `.sql`. Son rollback vit dans un fichier `<id>.rollback.sql` séparé (`yoyo/migrations.py::Migration.load`, `read_sql_migration` = `sqlparse.split` du fichier entier). Pour lui, `-- rollback` n'était qu'un commentaire, et tout ce qui suivait s'exécutait **à chaque apply forward** :
- 0008 : `ADD COLUMN session_nonce`, puis `DROP COLUMN session_nonce` ;
- 0010 : `ADD COLUMN user_id` et la FK, puis le drop de la FK et de la colonne ;
- 0012 : `ADD COLUMN email`, puis `DROP COLUMN email`.

Ce n'était donc pas un parseur qui « peut échouer » (formulation de l'ancienne règle 5), mais le comportement systématique de yoyo. Preuve : un `yoyo apply` sur une base vide affiche 12 résultats `SELECT 1`, ceux des blocs rollback no-op.

### Modifications

- `src/dashboard/migrate.py` (nouveau, ~250 lignes) — runner forward-only :
  - `split_statements()` découpe sur les `;` de premier niveau. Il gère les littéraux `'…'`, `"…"` et `` `…` ``, les quotes doublées (`''''` de 0009), les échappements `\`, et ignore les commentaires `-- `, `#` et `/* */`. Une erreur est levée sur un littéral ou un commentaire non terminé.
  - `forward_section()` coupe à la première ligne qui vaut exactement `-- rollback`. La prose « -- rollback between dev runs » de 0009 ou « -- rollback is a no-op… » de 0022 n'est pas un marqueur.
  - `load_migrations()` lit les fichiers en ordre lexical et vérifie que chaque `-- depends:` nomme un fichier antérieur.
  - `apply_migrations()` :
    - prend un verrou `GET_LOCK('kenboard_migrate.<db>', 30)` ;
    - fait un `CREATE TABLE IF NOT EXISTS _yoyo_migration`, avec le DDL de yoyo ;
    - saute les hash déjà présents ;
    - exécute les statements en autocommit ;
    - n'insère `(sha256(id), id, UTC_TIMESTAMP())` qu'une fois **tous** les statements réussis ;
    - lève `MigrationError("<id>, statement N: …")` en cas d'échec, sans enregistrer la migration ;
    - libère le verrou en `finally`.
  - `migrate()` ouvre une connexion PyMySQL directe : il n'y a plus de sous-processus, et le mot de passe n'apparaît plus dans argv ni dans `ps`.
- `src/dashboard/cli.py` — `migrate` et `migrate-test` appellent `_run_migrations()`. Une `MigrationError` donne le message « migration failed: … » et un exit 1. L'import `Path` inutilisé est retiré. L'interface ne change pas : `ansible/roles/kenboard/files/kenboard/update:184` appelle toujours `kenboard migrate`.
- `pyproject.toml` — retrait de `yoyo-migrations>=8.2` et de son ignore deptry DEP002 ; commentaire ruff mis à jour. `pdm lock` + `pdm sync --clean`.
- Documentation :
  - `CLAUDE.md` § Writing migrations : historique réécrit avec la vraie cause racine ; règle 5 devenue **Forward only** ; règles 4 et 6 sans mention de yoyo ; layout (`migrate.py`).
  - `doc/architecture.md` : table des couches, layout, « Cause racine », règles 4 à 6, principes.
  - `INSTALL.md` § Rollback : la commande `yoyo rollback` (avec mot de passe en clair) est remplacée par « pas de rollback, migration forward d'annulation ».
  - `ARCHITECTURE.md` : description de la section backend.
- About : `about.py` (docstring), `queries/about.sql` (commentaire), `templates/about.html` (« aucune trace yoyo » devient « aucune migration enregistrée »).
- `tests/sql/schema.sql` : commentaire d'en-tête.
- Les fichiers de migration ne sont pas touchés, même leurs commentaires qui citent yoyo (règle 4).
- `doc/dep-scorecard.{csv,md}` : snapshot généré par `pdm run dep-scorecard`, pas édité à la main.

### Comportements obtenus

- **Schéma identique à yoyo.** Sur `dashboard_test` vidé, on a comparé `yoyo apply` des 22 migrations et `kenboard migrate-test`. Le diff des `SHOW CREATE TABLE` et des lignes `(migration_hash, migration_id)` est vide ; seules diffèrent les tables internes de yoyo (`_yoyo_log`, `_yoyo_version`, `yoyo_lock`). Les positions de colonnes sont identiques, car 0009, 0011 et 0013 réajoutent au même endroit (`AFTER id` / `AFTER name` / en fin de table).
- **Reprise d'une base migrée par yoyo.** `yoyo apply` de 0001 à 0015, puis `kenboard migrate-test` : « 7 migration(s) applied, 15 already up to date », et un schéma identique à la référence.
- **Relance** : « 0 migration(s) applied, 22 already up to date ».
- **Verrou** : avec une autre session qui tient `kenboard_migrate.dashboard_test`, on obtient « another `kenboard migrate` holds the migration lock », sans aucun DDL exécuté.
- Les blocs `-- rollback` de 0008, 0010 et 0012 (avec `DROP`) ne sont plus jamais exécutés. Un test lit les vrais fichiers pour le vérifier.
- **Closure runtime** : 48 → 42 paquets. Sortent yoyo-migrations, sqlparse, tabulate, importlib-metadata, zipp et lazy-importer. Médiane du scorecard : 6.0 → 6.2.
- `_yoyo_log`, `_yoyo_version` et `yoyo_lock` restent en place sur les bases existantes, inertes. On peut les supprimer plus tard par une migration forward si on le souhaite.

### Garde-fous

- `tests/unit/test_migrate.py` (nouveau, 14 tests, sans base) : découpage (littéraux, quotes doublées, backticks, `5--3`, commentaires, cas non terminés), marqueur rollback contre la prose, `depends`, fichiers livrés (chaîne 0001→0022, aucun `DROP` en aller), apply partiel, échec non enregistré avec verrou relâché, verrou déjà pris, connexion autocommit. `migrate.py` est couvert à 100 %.
- `tests/unit/test_cli.py::TestMigrateCommands` réécrit (4 tests) : bonne base et bon compte DDL, `MigrationError` → exit 1, aucun `subprocess`.
- `pdm run check` : exit 0, 859 tests ; mypy, ruff, flake8 (DCO), interrogate 100 %, vulture, refurb et deptry propres.
- `pdm run py-malware` : GuardDog 0 bloquant, aucune entrée d'allowlist périmée, 42 paquets.
- `pdm run dep-scorecard` : 0 divergence ; seulement 6 notes « left the runtime closure ».
- Non fait, hors périmètre : la base de dev locale `dashboard` n'a que 19 migrations appliquées (0020 à 0022 en attente). Je ne l'ai pas migrée.
---

[← retour à backend/db](index.md) · [voir log](../../log/2026-11-26.md)
