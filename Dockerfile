# Multi-stage Dockerfile for Render Free Tier single container
# Stage 1: Build Vue 3 Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python 3.12 + Nginx
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=10000

WORKDIR /app

# Install system dependencies & Nginx & gettext (for envsubst)
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    gettext-base \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/pyproject.toml ./backend/
RUN pip install --upgrade pip && \
    pip install -e "./backend" && \
    pip install whitenoise

# Copy backend source
COPY backend/ ./backend/

# Copy built frontend assets from Stage 1 to /var/www/app
COPY --from=frontend-builder /app/frontend/dist /var/www/app

# Copy Nginx template and startup script
COPY infra/nginx/render.conf.template /etc/nginx/templates/render.conf.template
COPY render-entrypoint.sh /app/render-entrypoint.sh
RUN chmod +x /app/render-entrypoint.sh

# Run collectstatic
RUN cd backend && python manage.py collectstatic --noinput --settings=config.settings.prod || true

EXPOSE 10000

CMD ["/app/render-entrypoint.sh"]
