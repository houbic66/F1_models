#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/var/www/f1-models/repo"

if [ ! -d "$APP_DIR/.git" ]; then
  echo "Repository not found at $APP_DIR"
  echo "Clone it first:"
  echo "  git clone https://github.com/houbic66/F1_models.git $APP_DIR"
  exit 1
fi

cd "$APP_DIR"
git pull --ff-only

chown -R www-data:www-data "$APP_DIR"

nginx -t
systemctl reload nginx

echo "F1 models app deployed."

