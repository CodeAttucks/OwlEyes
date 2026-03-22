# Production Deployment Guide

For Azure migration and enterprise rollout, see `bead-platform/AZURE_PHASE2_PHASE3_RUNBOOK.md`.

## Database Setup Options

### Option A: Managed Database Service (Recommended)

#### AWS RDS
1. Create RDS instance with PostgreSQL 15 + PostGIS
2. Security groups: Allow inbound port 5432 from your app servers
3. Set master password securely
4. Copy endpoint to `DATABASE_URL`

#### Azure Database for PostgreSQL
1. Create server with PostGIS extension enabled
2. Allow Azure services access
3. Configure firewall rules
4. Connection string format: `postgresql://user:pass@server.postgres.database.azure.com:5432/bead`

#### Google Cloud SQL
1. Create PostgreSQL 15 instance
2. Enable PostGIS extension
3. Create database user and IP whitelisting
4. Connection string: `postgresql://user:pass@/bead?host=/cloudsql/project:region:instance`

### Option B: Self-Hosted Server

```bash
# Install PostgreSQL 15 with PostGIS on Ubuntu/Debian
sudo apt-get update
sudo apt-get install postgresql-15 postgresql-15-postgis-3

# Start service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql -c "CREATE DATABASE bead;"
sudo -u postgres psql -c "CREATE USER bead_user WITH ENCRYPTED PASSWORD 'strong_password';"
sudo -u postgres psql -c "ALTER ROLE bead_user WITH CREATEDB;"
sudo -u postgres psql -d bead -c "CREATE EXTENSION postgis;"

# Test connection
psql -h localhost -U bead_user -d bead -c "SELECT PostGIS_version();"
```

## Environment Configuration

Create `.env` with production values:

```
# Database
DATABASE_URL=postgresql://bead_user:password@db-prod.example.com:5432/bead
DB_PASSWORD=your_strong_password

# Application
SECRET_KEY=your_secret_key_here
DEBUG=false

# Frontend
VITE_BASE44_APP_ID=your_production_app_id
VITE_BASE44_APP_BASE_URL=https://bead-it.base44.app/api
NEXT_PUBLIC_MAPBOX_TOKEN=your_mapbox_token
NEXT_PUBLIC_POWERBI_EMBED_URL=your_powerbi_url

# Server
API_HOST=0.0.0.0
API_PORT=8000
```

## Deployment Steps

### 1. Database Migration
```bash
docker-compose -f docker-compose.prod.yml exec api python -m alembic upgrade head
```

### 2. Build Production Images
```bash
docker-compose -f docker-compose.prod.yml build
```

### 3. Start Services
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### 4. Verify Services
```bash
docker-compose -f docker-compose.prod.yml ps
# Check API: curl http://localhost:8000/health
# Check web: curl http://localhost:3000
```

## Security Checklist

| Readiness Item | Status | Owner | Target Date | Completed Date | Evidence |
| --- | --- | --- | --- | --- | --- |
| Enable SSL/TLS (nginx reverse proxy with Let's Encrypt) | In Progress | DevOps | 2026-03-29 |  | TLS listener and cert paths configured in nginx; cert files not yet present in staging container |
| Set strong database passwords | Verified in Staging | DBA | 2026-03-22 | 2026-03-22 | Password generator command produced 32-character value |
| Use environment variables for secrets (never commit .env) | Verified in Staging | DevOps | 2026-03-22 | 2026-03-22 | `bead-platform/.gitignore` includes `.env`; no tracked `.env` files in git index |
| Configure firewall rules (restrict DB access) | Partial | DevOps | 2026-03-29 |  | DB is not host-exposed in compose; host firewall tool unavailable in this staging container |
| Enable database backups (daily recommended) | In Progress | DBA | 2026-03-29 |  | `pg_dump` available; cron deployment pending |
| Set up monitoring and logging | Verified in Staging | SRE | 2026-03-22 | 2026-03-22 | Health checks present for `db`, `api`, and `web`; Docker logs available |
| Configure CORS for frontend domain | Verified in Staging | Backend Lead | 2026-03-22 | 2026-03-22 | API CORS allowlist contains `https://bead-it.base44.app` |
| Enable database audit logging | Pending | DBA | 2026-03-29 |  | `pgaudit` steps documented; not executed in staging yet |

### Security Checklist Implementation

Use this section as the completion guide for each checklist item.

#### 1) Enable SSL/TLS (nginx reverse proxy with Let's Encrypt)

`bead-platform/nginx.conf` already has `listen 443 ssl` and cert paths. Issue certificates on the host and mount `/etc/letsencrypt` into nginx (already configured in `bead-platform/docker-compose.prod.yml`).

```bash
# Install certbot on host
sudo apt-get update && sudo apt-get install -y certbot

# Stop nginx temporarily if certbot needs port 80
docker-compose -f bead-platform/docker-compose.prod.yml stop nginx

# Issue cert
sudo certbot certonly --standalone -d bead-it.base44.app -m admin@bead-it.base44.app --agree-tos --non-interactive

# Restart nginx with mounted certs
docker-compose -f bead-platform/docker-compose.prod.yml up -d nginx

# Auto-renew
echo "0 3 * * * root certbot renew --quiet && docker-compose -f /workspaces/OwlEyes/bead-platform/docker-compose.prod.yml restart nginx" | sudo tee /etc/cron.d/certbot-renew
```

#### 2) Set strong database passwords

```bash
# Generate a 32-char password
openssl rand -base64 48 | tr -dc 'A-Za-z0-9!@#$%^&*()_+-=' | head -c 32
echo
```

Set this value in `.env` as `DB_PASSWORD` and use a separate strong value for `SECRET_KEY`.

#### 3) Use environment variables for secrets

- Keep secrets in `.env` (or Azure Key Vault / AWS Secrets Manager in hosted environments).
- Ensure `.env` is ignored:

```bash
grep -qxF '.env' .gitignore || echo '.env' >> .gitignore
chmod 600 .env
```

#### 4) Configure firewall rules (restrict DB access)

Your compose file already avoids exposing DB publicly (`expose: 5432` instead of `ports`). Also lock down host firewall:

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 5432/tcp
sudo ufw enable
sudo ufw status verbose
```

#### 5) Enable database backups (daily recommended)

Create a daily backup script and cron job:

```bash
cat > /usr/local/bin/bead-db-backup.sh << 'EOF'
#!/usr/bin/env bash
set -euo pipefail
TS=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/var/backups/owleyes/bead
mkdir -p "$BACKUP_DIR"
pg_dump "$DATABASE_URL" | gzip > "$BACKUP_DIR/bead_${TS}.sql.gz"
find "$BACKUP_DIR" -type f -name 'bead_*.sql.gz' -mtime +14 -delete
EOF

sudo chmod +x /usr/local/bin/bead-db-backup.sh
echo "0 2 * * * root /usr/local/bin/bead-db-backup.sh" | sudo tee /etc/cron.d/bead-db-backup
```

#### 6) Set up monitoring and logging

- Application logs: `docker-compose -f bead-platform/docker-compose.prod.yml logs -f api web nginx`
- Health checks are already configured in `bead-platform/docker-compose.prod.yml` for `api`, `web`, and `db`.
- Add centralized log shipping (for example, Azure Monitor, CloudWatch, or ELK) before go-live.

#### 7) Configure CORS for frontend domain

`bead-platform/api/main.py` already includes `https://bead-it.base44.app` in CORS origins. Keep this list strict and avoid wildcard origins in production.

#### 8) Enable database audit logging

For PostgreSQL, enable `pgaudit` and restart DB:

```sql
-- Run as superuser
CREATE EXTENSION IF NOT EXISTS pgaudit;
ALTER SYSTEM SET shared_preload_libraries = 'pgaudit';
ALTER SYSTEM SET pgaudit.log = 'read,write,ddl,role';
ALTER SYSTEM SET pgaudit.log_parameter = on;
SELECT pg_reload_conf();
```

If `shared_preload_libraries` changes are not applied by reload, restart the PostgreSQL service/container.

### Staging Execution and Verification (2026-03-22)

The following checks were executed in the staging dev container.

For repeatable CI validation, run:

```bash
chmod +x bead-platform/scripts/validate-staging-security.sh
bead-platform/scripts/validate-staging-security.sh
```

Optional live DB audit validation:

```bash
VALIDATE_DB_AUDIT=1 DATABASE_URL="postgresql://..." bead-platform/scripts/validate-staging-security.sh
```

| Item | Command or Evidence | Result |
| --- | --- | --- |
| 1. SSL/TLS | `docker run ... nginx:alpine nginx -t` with mapped `bead-platform/nginx.conf` | Failed in staging because Let's Encrypt cert files are not present (`/etc/letsencrypt/live/bead-it.base44.app/...` missing). Config references are correct. |
| 2. Strong DB passwords | `openssl rand ... | head -c 32` | Passed (`generated_password_length=32`). |
| 3. Env vars for secrets | `grep -qxF '.env' bead-platform/.gitignore` and `git ls-files | grep -E '(^|/)\.env$'` | Passed (`bead-platform/.gitignore` contains `.env`; no tracked `.env` files). |
| 4. Firewall rules / DB access | `docker compose -f bead-platform/docker-compose.prod.yml config` and rendered config parse | Passed for compose isolation (`db_has_ports=false`, `db_has_expose=true`); host firewall not verifiable in this container (`ufw_unavailable`). |
| 5. DB backups | `pg_dump --version` | Passed for tooling availability (`pg_dump (PostgreSQL) 16.13`); scheduled cron backup not yet deployed in staging. |
| 6. Monitoring and logging | `grep` evidence in `bead-platform/docker-compose.prod.yml` | Passed (`healthcheck` configured for `db`, `api`, and `web`). |
| 7. CORS domain | `grep` evidence in `bead-platform/api/main.py` | Passed (`https://bead-it.base44.app` allowlisted). |
| 8. DB audit logging | SQL commands documented in this guide | Pending execution in live DB session (requires superuser and DB restart). |

## Backing Up Production Data

```bash
# Backup
pg_dump -U bead_user -h db.example.com bead > backup-$(date +%Y%m%d).sql

# Restore
psql -U bead_user -h db.example.com bead < backup-20260320.sql
```
