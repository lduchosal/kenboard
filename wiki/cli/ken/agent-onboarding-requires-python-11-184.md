---
id: 184
title: "AGENT / Onboarding requires python 11+"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:41
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: cli/ken
section_title: "ken task CLI"
---

# #184 — AGENT / Onboarding requires python 11+

In the agent onboarding page, tell the agent it needs python 11+ and a venv

---

## Résolution

### Modifications
- `src/dashboard/onboarding.py` — added Python 11+ and venv prerequisites to all three onboarding renderers: `onboarding_text_full` (200 route), `onboarding_text` (401 text body), and `onboarding_json` (401 JSON body)

### Comportements obtenus
- The full onboarding runbook (served at `/onboard/cat/.../project/...`) now shows a **Pré-requis** section with Python 11+ requirement and venv creation commands before the install step
- The 401 text body for non-browser clients includes a prerequisites line with venv activation command
- The 401 JSON body includes a new `prerequisites` field in the onboarding object

### Garde-fous
- `pdm run lint` — passed
- `pdm run typecheck` — passed
- `pdm run test-quick` — 269 passed
---

[← retour à cli/ken](index.md) · [voir log](../../log.md)
