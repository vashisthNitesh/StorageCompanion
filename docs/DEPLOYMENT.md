# Single-Server Production Deployment Guide

This guide details how to deploy SpeedCloud / CloudVault on a single VPS (e.g. Hetzner, DigitalOcean, AWS EC2) using Docker Compose and Cloudflare R2.

---

## 1. Architecture Summary

Everything runs on a **single VPS**:
- **Nginx** (:80 / :443): Handles TLS, serves compiled Vue 3 SPA assets (`frontend/dist`), and reverse-proxies `/api/` to Gunicorn.
- **Gunicorn + Uvicorn workers** (:8000): Django 5 + DRF backend.
- **PostgreSQL 16**: Primary metadata store.
- **Redis 7**: Cache, session blacklist, and Celery broker.
- **Celery Worker & Beat**: Quota reconciliation and stale upload cleanup.
- **Cloudflare R2**: Global object storage with **Zero Egress Fees**. Files never proxy through Nginx or Gunicorn.

---

## 2. Server Provisioning

### Recommended Specs
- 2 vCPUs, 4 GB RAM, 40 GB NVMe SSD.
- Ubuntu 22.04 / 24.04 LTS.

### 1. Install Docker & Compose
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

### 2. Configure Firewall (ufw)
```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

---

## 3. Environment Variables (`.env.prod`)

Create `.env.prod` on the server:

```ini
ENVIRONMENT=prod
DEBUG=False
DOMAIN=vault.yourdomain.com
SECRET_KEY=generate-a-strong-64-character-secret-key

# Database
POSTGRES_DB=speedcloud_prod
POSTGRES_USER=speedcloud_user
POSTGRES_PASSWORD=generate-strong-db-password
DATABASE_URL=postgres://speedcloud_user:generate-strong-db-password@db:5432/speedcloud_prod

# Redis & Celery
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Cloudflare R2 (S3 Compatible API)
STORAGE_BACKEND=r2
S3_ENDPOINT_URL=https://<ACCOUNT_ID>.r2.cloudflarestorage.com
S3_ACCESS_KEY_ID=<R2_ACCESS_KEY_ID>
S3_SECRET_ACCESS_KEY=<R2_SECRET_ACCESS_KEY>
S3_BUCKET_NAME=speedcloud-production
S3_REGION_NAME=auto
PRESIGNED_URL_TTL=900

# Payments (Razorpay)
PAYMENT_PROVIDER=razorpay
DEFAULT_CURRENCY=INR
RAZORPAY_KEY_ID=rzp_live_...
RAZORPAY_KEY_SECRET=...
RAZORPAY_WEBHOOK_SECRET=...
```

---

## 4. Cloudflare R2 Bucket Configuration

In Cloudflare Dashboard:
1. Navigate to **R2** > **Create bucket** > `speedcloud-production`.
2. Ensure **Public Access is disabled**.
3. Under **CORS Policy**, add:
```json
[
  {
    "AllowedOrigins": ["https://vault.yourdomain.com"],
    "AllowedMethods": ["GET", "PUT", "HEAD"],
    "AllowedHeaders": ["*"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3600
  }
]
```

---

## 5. SSL / TLS Setup (Certbot)

Run Certbot to acquire Let's Encrypt certificates:
```bash
mkdir -p infra/certbot/conf infra/certbot/www
docker run -it --rm --name certbot \
  -v "$(pwd)/infra/certbot/conf:/etc/letsencrypt" \
  -v "$(pwd)/infra/certbot/www:/var/www/certbot" \
  certbot/certbot certonly --webroot -w /var/www/certbot \
  -d vault.yourdomain.com --email admin@yourdomain.com --agree-tos --no-eff-email
```

---

## 6. Build and Launch

Build the frontend on your development machine or CI (never on a small VPS):
```bash
npm --prefix frontend run build
```

Then run on the VPS:
```bash
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml exec web python manage.py migrate
docker compose -f docker-compose.prod.yml exec web python manage.py seed_demo
```

---

## 7. Automated Backups

Set up a daily cron job for Postgres backups:
```bash
0 2 * * * docker compose -f /opt/speedcloud/docker-compose.prod.yml exec -T db pg_dump -U speedcloud_user speedcloud_prod | gzip > /opt/backups/db_$(date +\%F).sql.gz
```
