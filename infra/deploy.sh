#!/usr/bin/env bash
set -euo pipefail

echo "==> Deploying SpeedCloud on single VPS..."

# 1. Pull latest code
git pull origin main

# 2. Build production frontend assets (if running in CI or local container)
echo "==> Verifying compiled frontend assets..."
if [ ! -d "frontend/dist" ]; then
  echo "Error: frontend/dist not found. Compile frontend assets in CI before deploy."
  exit 1
fi

# 3. Pull / Build containers
docker compose -f docker-compose.prod.yml build web celery_worker celery_beat

# 4. Run database migrations
docker compose -f docker-compose.prod.yml run --rm web python manage.py migrate --noinput

# 5. Zero-downtime restart of application processes
docker compose -f docker-compose.prod.yml up -d --remove-orphans

# 6. Reload nginx
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload || true

echo "==> Deployment successful!"
