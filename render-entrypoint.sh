#!/bin/bash
set -e

echo "==> SmartSpace starting..."
PORT=${PORT:-10000}

# 1. Substitute PORT into nginx config
mkdir -p /etc/nginx/conf.d
envsubst '$PORT' < /etc/nginx/templates/render.conf.template > /etc/nginx/conf.d/default.conf
rm -f /etc/nginx/sites-enabled/default

# 2. Database migrations
cd /app/backend
python manage.py migrate --noinput

# 3. Plans and (optionally) the master admin from MASTER_ADMIN_EMAIL / MASTER_ADMIN_PASSWORD
python manage.py seed_plans
python manage.py create_master_admin

# 4. Gunicorn with threaded WSGI workers. Django views are synchronous, so threads let a
#    slow storage transfer run without blocking every other request. Each in-flight upload
#    part holds one thread while it streams to storage, so leave plenty for everything else.
gunicorn config.wsgi:application \
  --bind 127.0.0.1:8000 \
  --workers "${WEB_CONCURRENCY:-1}" \
  --threads "${GUNICORN_THREADS:-24}" \
  --worker-class gthread \
  --timeout 300 \
  --keep-alive 65 \
  --access-logfile - &

# 5. nginx in the foreground on $PORT
exec nginx -g "daemon off;"
