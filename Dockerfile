# Single container for Render: nginx serves the Vue SPA and proxies /api to Gunicorn.

# Stage 1: build the Vue 3 frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python 3.12 + nginx
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=10000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    gettext-base \
    && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml ./backend/
COPY backend/apps ./backend/apps
COPY backend/config ./backend/config
COPY backend/manage.py ./backend/manage.py
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir "./backend"

COPY --from=frontend-builder /app/frontend/dist /var/www/app

COPY infra/nginx/render.conf.template /etc/nginx/templates/render.conf.template
COPY render-entrypoint.sh /app/render-entrypoint.sh
RUN chmod +x /app/render-entrypoint.sh

RUN cd backend && SECRET_KEY=collectstatic-only python manage.py collectstatic --noinput --settings=config.settings.prod

EXPOSE 10000

CMD ["/app/render-entrypoint.sh"]
