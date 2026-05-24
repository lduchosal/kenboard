---
wiki:
  sections:
    - id: backend
      title: Backend (Flask / Python)
      description: Application factory, blueprints, request middleware, server-side logic.
      sub:
        - id: api
          title: REST API
          description: /api/v1/* endpoints, request validation, JSON serialization.
        - id: auth
          title: Authentication & permissions
          description: Cookie sessions, OIDC, API keys, scope checks, CSRF.
        - id: db
          title: Database (SQL + migrations)
          description: aiosql queries, yoyo migrations, schema, PyMySQL connection.
        - id: perf
          title: Performance & observability
          description: Request perf budget, structlog setup, monitoring hooks.
        - id: email
          title: Email & notifications
          description: SMTP wrapper, password reset, email verification flows.
    - id: frontend
      title: Frontend (templates + JS)
      description: Server-rendered Jinja2 + vanilla JS bundle (Vite).
      sub:
        - id: pages
          title: Page templates (Jinja2)
          description: /, /cat/<id>.html, /admin/*, /login, /register, partials.
        - id: js
          title: JS modules
          description: ES modules under static/js/ (api.js, tasks.js, keyboard.js, ...).
        - id: ux
          title: UX / interactions
          description: Drag & drop, modals, keyboard shortcuts, markdown rendering.
        - id: a11y
          title: Accessibility
          description: ARIA semantics, keyboard nav, native HTML elements.
    - id: cli
      title: Command-line interface
      description: kenboard admin CLI and ken task CLI.
      sub:
        - id: kenboard
          title: kenboard admin CLI
          description: serve, prod, migrate, migrate-test, set-password, snapshot.
        - id: ken
          title: ken task CLI
          description: list/show/add/update/move/done + wiki subcommands.
    - id: wiki
      title: Wiki (#376)
      description: LLM-wiki pattern (Karpathy) — classification, sync, build, lint.
    - id: ops
      title: Ops & deployment
      description: Ansible role, FreeBSD rc.d, update workflow, packaging, PyPI publish.
    - id: quality
      title: Code quality & CI
      description: Tests (unit/integration/e2e), lint, typecheck, coverage, Sonarcloud.
    - id: docs
      title: Documentation
      description: README, agent_guide.md, doc/*.md, OpenAPI schema, CLAUDE.md.
---

# kenboard — wiki schema

Frontmatter ci-dessus = source de vérité pour `ken wiki *`. Pour la
documentation d'architecture détaillée (stack, schéma DB, flux de
requête, règles de migration), voir [`doc/architecture.md`](doc/architecture.md).

Le pattern de wiki implémenté ici est inspiré du *LLM Wiki* de Karpathy :
<https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f>.
