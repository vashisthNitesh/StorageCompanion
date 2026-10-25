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
- Gunicorn runs threaded WSGI workers (`WEB_CONCURRENCY` × `GUNICORN_THREADS`, default 1 × 32). Upload
  parts and downloads each have their own cap per worker (`UPLOAD_SLOTS`, `DOWNLOAD_SLOTS`, default 12
  each), leaving 8 threads for everything else; see "Capacity" below.
- On every start the entrypoint runs migrations, `seed_plans` and `create_master_admin`
  (from `MASTER_ADMIN_EMAIL` / `MASTER_ADMIN_PASSWORD`).
- There is no background worker: plan expiry runs from the admin console ("Run expiry check")
  or `manage.py process_expired_subscriptions` on a schedule.

## Storage
SpaceByte is the only storage backend. Without `SPACEBYTE_ACCESS_TOKEN` the client returns mock
responses in `DEBUG` (local development and tests) and fails loudly in production.

### Uploads
1. `POST /api/v1/uploads` opens a SpaceByte multipart upload (8 MiB plaintext parts, larger only
   when a file would otherwise need more than 9,500 parts) and presigns the first 8 parts. Small
   parts mean a pause or dropped connection only re-sends the few parts in flight.
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

## Capacity
Measured with a local copy of production (same gunicorn settings, Postgres, a fake SpaceByte with
250 ms API latency; virtual users browsing with ~3 s between actions):

| Server | Users browsing at once | Typical / slowest 5% response |
|---|---|---|
| Render free (0.1 CPU) | 25 | 0.85 s / 2.1 s (overloaded beyond this) |
| 1 worker on one full core | 500 | ~10 ms / ~15 ms |
| 1 worker on one full core | 1,000 | 0.55 s / 0.75 s (saturated) |
| 4 workers on 2 CPUs | 1,000 | ~90 ms / ~550 ms, no errors, ~650 MB RAM |

- One Python worker uses at most one CPU. Set `WEB_CONCURRENCY` to about the number of CPUs (more
  workers than CPUs was slower in testing); each worker needs ~150–200 MB.
- File bytes pass through the server, so each running upload part or download occupies a thread.
  The per-worker slot caps keep browsing fast while others transfer (slowest 5% of folder loads
  stayed ~20 ms with 10 people uploading, versus ~6 s without caps); extra transfers get 503 +
  `Retry-After` and the app retries them. Raise `GUNICORN_THREADS` (and the slots) on larger
  instances. Serving 1,000 simultaneous uploaders needs browser-to-storage transfers instead.
- Sign-in hashing (Argon2id, 19 MiB) runs within a memory budget (`PASSWORD_HASH_MEMORY_MB`,
  default 128), so a burst of sign-ins queues briefly instead of exhausting memory (48 at once:
  186 MB peak, versus 665 MB with Django's defaults).
- Rate limits are per account (sign-in) and per device (token refresh), with generous per-IP
  backstops, because many people share an IP on mobile networks and offices. The client IP comes
  from Cloudflare's `CF-Connecting-IP` (`CLIENT_IP_HEADER`); X-Forwarded-For can be forged.
- Database connections are reused for 60 s with health checks (`CONN_MAX_AGE`), and server-side
  cursors are off for Neon's pooler. Use the pooled (`-pooler`) Neon connection string.

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
