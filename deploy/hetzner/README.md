# Hetzner Deployment

This deployment is for a clean Hetzner VPS running Ubuntu/Debian.

The public GitHub repository contains only source code and documentation. Private/generated data is intentionally not stored in Git:

- `app/data/app-data.json`
- `app/data/model_photo_overrides.json`
- private Excel workbooks
- scraped page cache

For a working production app, copy the generated JSON data to the server after the source code is deployed.

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
apt install -y git nginx
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

