# SpeedCloud System Architecture

## 1. Single-Server VPS Deployment Topology

```
                                  Client Browser
                                        │
                         ┌──────────────┴──────────────┐
                         ▼                             ▼
             Vite Built Assets & API           Direct Binary Streams
             https://vault.speedcloud.app      https://*.r2.cloudflarestorage.com
                         │
                         ▼
             Nginx (Port 80 / 443)
             ├── /             ──► Serves static /var/www/app (dist/)
             ├── /assets/      ──► 1-year immutable cache
             ├── /api/         ──► Reverse-proxy to Gunicorn (127.0.0.1:8000)
             └── /django-admin/──► Reverse-proxy to Gunicorn
                         │
                         ▼
             Gunicorn + Uvicorn Workers (Port 8000)
             Django 5.x + Django REST Framework
                         │
             ┌───────────┼───────────┐
             ▼           ▼           ▼
        PostgreSQL 16  Redis 7    Celery Worker & Beat
        (Metadata)     (Sessions) (Nightly Reconciliation)
```

## 2. Zero-Knowledge Guarantees

1. **Client-Side Key Derivation**: KEK is derived via WebAssembly Argon2id in the browser.
2. **Deterministic Nonces**: Each chunk $i$ is encrypted with $Nonce_{base} \oplus i$ preventing nonce reuse.
3. **Fragment-Based Links**: Decryption keys for public links reside in `https://domain/s/token#key=...`. Per RFC 3986, fragments are never transmitted to HTTP servers.
4. **Offline Recovery Phrase**: 24-word BIP-39 mnemonic phrase wraps a secondary copy of the Master Key.
