# Retyped

Podcast discovery platform at [retyped.xyz](https://retyped.xyz).

- [`apps/web`](apps/web) — Next.js frontend ([README](apps/web/README.md))
- [`apps/api`](apps/api) — Django API and Celery workers ([README](apps/api/README.md))
- [`deploy`](deploy) — how pushes to `main` reach the server ([README](deploy/README.md))

This repo was formed on 2026-11-17 by merging `nuwaves/retyped_frontend` and `nuwaves/retyped_processing` with their full histories. Tags from those repos are prefixed `web-` and `api-`.

## Local development

Both apps' compose files join an external Docker network, so create it once:

```bash
docker network create retyped-local
```

Then run each app from its own directory (see its README).
