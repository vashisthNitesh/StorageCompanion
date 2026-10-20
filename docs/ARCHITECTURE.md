# SmartSpace Architecture

## Deployment (Render, single Docker container)

```
Browser ──HTTPS──▶ Render edge ──▶ nginx :$PORT
                                    ├─ /            Vue SPA (static, built at image build time)
                                    ├─ /assets/     hashed static assets (1 year cache)
                                    └─ /api/, /django-admin/, /static/ ─▶ Gunicorn :8000
                                                                           (Django + DRF, gthread workers)
Gunicorn ──▶ PostgreSQL (Neon, DATABASE_URL)
         ──▶ SpaceByte API (encrypted parts, downloads)
         ──▶ Razorpay API (orders)  ◀── Razorpay webhooks
```

- One deployment path: `Dockerfile` + `render.yaml` + `render-entrypoint.sh` + `infra/nginx/render.conf.template`.
- Gunicorn runs threaded WSGI workers (`WEB_CONCURRENCY` × `GUNICORN_THREADS`, default 1 × 8), so slow
  storage transfers don't block other requests.
- On every start the entrypoint runs migrations, `seed_plans` and `create_master_admin`
  (from `MASTER_ADMIN_EMAIL` / `MASTER_ADMIN_PASSWORD`).
- There is no background worker: plan expiry runs from the admin console ("Run expiry check")
  or `manage.py process_expired_subscriptions` on a schedule.

## Storage
SpaceByte is the only storage backend. Without `SPACEBYTE_ACCESS_TOKEN` the client returns mock
responses in `DEBUG` (local development and tests) and fails loudly in production.

## Privacy model
Files and names are encrypted in the browser (see `CRYPTO.md`). The server stores ciphertext,
wrapped keys, folder structure, sizes and timestamps.

## Local development
```
cd backend && uv sync --extra dev   # or: python -m venv .venv && pip install -e ".[dev]"
make migrate seed dev-backend       # Django on :8000 (SQLite by default)
make dev-frontend                   # Vite on :5173, proxies /api
make test                           # backend tests always use in-memory SQLite
```
Set `API_PROXY_TARGET` if the backend runs on another port.
