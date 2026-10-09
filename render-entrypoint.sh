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

# 3. Seed subscription plans & ensure master admin
echo "==> Seeding subscription plans and master admin..."
python manage.py seed_plans || true
python manage.py create_master_admin || true

# 4. Start Gunicorn in the background on 127.0.0.1:8000
echo "==> Starting Gunicorn on 127.0.0.1:8000..."
# WSGI + gthread: every request gets a real thread, StreamingHttpResponse streams natively
# (no ASGI sync-iterator buffering), and a slow upload/download can't starve an event loop.
# nginx buffers relay part bodies (see render.conf.template) so slow clients don't pin threads.
gunicorn config.wsgi:application --bind 127.0.0.1:8000 \
  --worker-class gthread --workers "${WEB_CONCURRENCY:-2}" --threads "${GUNICORN_THREADS:-8}" \
  --timeout 600 --graceful-timeout 30 --keep-alive 65 \
  --access-logfile - --error-logfile - &

# 5. Start Nginx in the foreground on $PORT
echo "==> Starting Nginx on port ${PORT}..."
exec nginx -g "daemon off;"
