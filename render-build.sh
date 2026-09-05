#!/usr/bin/env bash
# Script for Render Native Python Web Service (Build Command)
set -o errexit

echo "==> Building frontend Vue 3 static bundle..."
npm --prefix frontend install
npm --prefix frontend run build

echo "==> Installing Python dependencies..."
python -m pip install --upgrade pip
python -m pip install -e "./backend"
python -m pip install whitenoise

echo "==> Collecting Django static files..."
cd backend
python manage.py collectstatic --noinput --settings=config.settings.prod || true
