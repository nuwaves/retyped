# Retyped

Monorepo for [retyped.xyz](https://retyped.xyz), a podcast discovery platform.

| Path | What | Details |
|---|---|---|
| `apps/web/` | Next.js frontend | `apps/web/CLAUDE.md` |
| `apps/api/` | Django REST API, admin, Celery workers (feed ingest, transcription, LLM processing) | `apps/api/CLAUDE.md` |
| `deploy/` | Server-side deploy scripts for the Hetzner box | `deploy/README.md` |
| `.github/workflows/` | CI and deploys, one set per app (`web-*.yml`, `api-*.yml`) | |

Each app keeps its own toolchain: run npm commands from `apps/web/` and Python/Django commands from `apps/api/`. There is no root `package.json` or workspace tool.

## CI and deploys

- Workflows are path-filtered: a change under `apps/web/` runs only the web checks and deploys only the frontend; `apps/api/` likewise. A PR touching both runs both.
- **Every push to `main` that touches an app deploys that app to production.** Work on a branch and open a PR into `main`. Never push to `main` directly.
- Images keep their pre-monorepo names: `ghcr.io/nuwaves/retyped_frontend` and `ghcr.io/nuwaves/retyped_processing`.
- Cross-app changes (an API field the frontend starts reading, say) can land in one PR, but the two apps deploy independently, so keep the API backwards-compatible with the frontend that is live.

Never commit `.env*` files or secrets.
