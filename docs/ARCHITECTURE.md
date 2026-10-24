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
- Gunicorn runs threaded WSGI workers (`WEB_CONCURRENCY` × `GUNICORN_THREADS`, default 1 × 24), so slow
  storage transfers don't block other requests.
- On every start the entrypoint runs migrations, `seed_plans` and `create_master_admin`
  (from `MASTER_ADMIN_EMAIL` / `MASTER_ADMIN_PASSWORD`).
- There is no background worker: plan expiry runs from the admin console ("Run expiry check")
  or `manage.py process_expired_subscriptions` on a schedule.

## Storage
SpaceByte is the only storage backend. Without `SPACEBYTE_ACCESS_TOKEN` the client returns mock
responses in `DEBUG` (local development and tests) and fails loudly in production.

### Uploads
1. `POST /api/v1/uploads` opens a SpaceByte multipart upload (20 MB plaintext parts, 32 MB above
   50 GB) and presigns the first 8 parts.
2. The browser encrypts each part and `POST`s it to `/api/v1/uploads/<id>/parts/<n>`, four parts
   at a time per file. The server checks the declared length against the file size and streams
   the body to the part's presigned URL as it arrives (nothing is buffered in memory). Part URLs
   are signed just in time in batches of 8 and reused for 5 minutes; a URL that storage rejects
   is dropped so the retry gets a fresh one.
3. `POST /api/v1/uploads/<id>/complete` verifies every part's size, completes the upload and
   records the file.

The browser retries a part until it's stored or the person cancels: offline waits for the
connection, timeouts / 429 / 5xx back off (1 s → 30 s with jitter), a stalled transfer (no progress
for 60 s) is restarted, and a lost session (404 / 409) opens a new one. Only definitive answers
(400, 402, 403, 411, 413, 422) stop an upload; "Retry" resumes from the parts already stored.

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
