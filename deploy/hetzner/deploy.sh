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
git config --global --add safe.directory "$APP_DIR"
git pull --ff-only

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y python3-venv

python3 -m venv /var/www/f1-models/venv
/var/www/f1-models/venv/bin/python -m pip install --upgrade pip
/var/www/f1-models/venv/bin/python -m pip install -r "$APP_DIR/app/backend/requirements.txt"

mkdir -p /etc/f1-models
if [ ! -f /etc/f1-models/job-server.env ]; then
  TOKEN="$(/var/www/f1-models/venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(32))')"
  printf "F1_ADMIN_TOKEN=%s\nF1_JOB_HOST=127.0.0.1\nF1_JOB_PORT=8765\n" "$TOKEN" > /etc/f1-models/job-server.env
  chmod 600 /etc/f1-models/job-server.env
fi

cp "$APP_DIR/deploy/hetzner/f1-jobs.service" /etc/systemd/system/f1-jobs.service
systemctl daemon-reload
systemctl enable f1-jobs.service
systemctl restart f1-jobs.service

chown -R www-data:www-data "$APP_DIR"

nginx -t
systemctl reload nginx

echo "F1 models app deployed."
