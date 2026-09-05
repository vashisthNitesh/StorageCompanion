#!/bin/bash
set -e

echo "==> SpeedCloud starting on Render..."
PORT=${PORT:-10000}

# 1. Substitute PORT into Nginx config
echo "==> Configuring Nginx to listen on port ${PORT}..."
mkdir -p /etc/nginx/conf.d
envsubst '$PORT' < /etc/nginx/templates/render.conf.template > /etc/nginx/conf.d/default.conf

# 2. Run database migrations automatically
echo "==> Running Django database migrations..."
cd /app/backend
python manage.py migrate --noinput

# 3. Seed initial plans & demo account automatically
echo "==> Seeding initial subscription plans & demo account..."
python manage.py seed_demo || true

# 4. Start Gunicorn in the background on 127.0.0.1:8000
echo "==> Starting Gunicorn on 127.0.0.1:8000..."
gunicorn config.asgi:application --bind 127.0.0.1:8000 --workers 2 -k uvicorn.workers.UvicornWorker &

# 5. Start Nginx in the foreground on $PORT
echo "==> Starting Nginx on port ${PORT}..."
exec nginx -g "daemon off;"
