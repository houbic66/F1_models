# Hetzner Deployment

This deployment is for a clean Hetzner VPS running Ubuntu/Debian.

The public GitHub repository contains only source code and documentation. Private/generated data is intentionally not stored in Git:

- `app/data/app-data.json`
- `app/data/model_photo_overrides.json`
- private Excel workbooks
- scraped page cache

For a working production app, copy the generated JSON data to the server after the source code is deployed.

## Create The Hetzner Server

1. Sign in to Hetzner Cloud Console:

```text
https://console.hetzner.cloud/
```

2. Create a new project, for example:

```text
F1 Models
```

3. Create a new server with these settings:

```text
Location: Germany or Finland
Image: Ubuntu 24.04 LTS
Type: Shared vCPU, smallest x86 plan with at least 2 vCPU / 4 GB RAM / 40 GB disk
Networking: IPv4 enabled
SSH key: your local SSH key, or password login if you do not have a key yet
Name: f1-models
Backups: optional
```

The app is currently a static web app served by Nginx, so it does not need a large server. If a backend database or automated scraping worker is added later, the same server can be resized.

4. After the server is created, Hetzner will show the server IP address. Use that IP as `SERVER_IP` in the commands below.

5. If you used password login, copy the temporary root password from the Hetzner email or console.

Connect from Windows PowerShell:

```powershell
ssh root@SERVER_IP
```

The first login may ask whether to trust the server fingerprint. Type:

```text
yes
```

## Server Layout

Recommended paths:

```text
/var/www/f1-models/repo      Git checkout
/var/www/f1-models/shared    Private generated data
/var/www/f1-models/logs      Optional logs
```

The public web root is:

```text
/var/www/f1-models/repo/app
```

The private data files should be placed in:

```text
/var/www/f1-models/repo/app/data/app-data.json
/var/www/f1-models/repo/app/data/model_photo_overrides.json
```

## Fresh Server Setup

Run as `root` or with `sudo`:

```bash
apt update
apt install -y git nginx python3-venv
mkdir -p /var/www/f1-models
chown -R www-data:www-data /var/www/f1-models
```

Clone the repo:

```bash
cd /var/www/f1-models
git clone https://github.com/houbic66/F1_models.git repo
chown -R www-data:www-data /var/www/f1-models/repo
```

Install Nginx config:

```bash
cp /var/www/f1-models/repo/deploy/hetzner/nginx-site.conf /etc/nginx/sites-available/f1-models
ln -s /etc/nginx/sites-available/f1-models /etc/nginx/sites-enabled/f1-models
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx
```

Install the background job service:

```bash
mkdir -p /etc/f1-models
TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
printf "F1_ADMIN_TOKEN=%s\nF1_JOB_HOST=127.0.0.1\nF1_JOB_PORT=8765\n" "$TOKEN" > /etc/f1-models/job-server.env
chmod 600 /etc/f1-models/job-server.env

python3 -m venv /var/www/f1-models/venv
/var/www/f1-models/venv/bin/python -m pip install --upgrade pip
/var/www/f1-models/venv/bin/python -m pip install -r /var/www/f1-models/repo/app/backend/requirements.txt

cp /var/www/f1-models/repo/deploy/hetzner/f1-jobs.service /etc/systemd/system/f1-jobs.service
systemctl daemon-reload
systemctl enable f1-jobs.service
systemctl restart f1-jobs.service
```

Show the admin token used by the app's `Ulohy` tab:

```bash
cat /etc/f1-models/job-server.env
```

Open firewall if needed:

```bash
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw enable
```

## Upload Private Generated Data

From your local machine:

```powershell
scp app/data/app-data.json root@SERVER_IP:/var/www/f1-models/repo/app/data/app-data.json
scp app/data/model_photo_overrides.json root@SERVER_IP:/var/www/f1-models/repo/app/data/model_photo_overrides.json
```

For year-processing jobs, also upload the private working inputs that are not stored in the public GitHub repository:

```powershell
tar -czf f1-private-runtime.tgz outputs/model_catalog outputs/wiki_audit input app/data/photo_page_cache app/data/app-data.json app/data/model_photo_overrides.json
scp f1-private-runtime.tgz root@SERVER_IP:/tmp/f1-private-runtime.tgz
```

Then on the server:

```bash
cd /var/www/f1-models/repo
tar -xzf /tmp/f1-private-runtime.tgz
find outputs input app/data/photo_page_cache -type d -exec chmod 755 {} +
find outputs input app/data/photo_page_cache -type f -exec chmod 644 {} +
chmod 644 app/data/*.json
```

Then on the server:

```bash
chown www-data:www-data /var/www/f1-models/repo/app/data/*.json
systemctl reload nginx
```

## Update Existing Deployment

On the server:

```bash
cd /var/www/f1-models/repo
git pull --ff-only
chown -R www-data:www-data /var/www/f1-models/repo
nginx -t
systemctl reload nginx
```

Or use:

```bash
bash /var/www/f1-models/repo/deploy/hetzner/deploy.sh
```

The deploy script also updates/restarts the background job service and keeps the existing admin token.

## Domain

Before using a domain, point an `A` record to the Hetzner server IP.

Then edit:

```text
/etc/nginx/sites-available/f1-models
```

Replace:

```text
server_name _;
```

with:

```text
server_name your-domain.example www.your-domain.example;
```

Reload:

```bash
nginx -t
systemctl reload nginx
```

HTTPS can be added later with Certbot.
