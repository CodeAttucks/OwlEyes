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
VITE_BASE44_APP_BASE_URL=https://bead-it.org/api
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

- [ ] Enable SSL/TLS (nginx reverse proxy with Let's Encrypt)
- [ ] Set strong database passwords
- [ ] Use environment variables for secrets (never commit .env)
- [ ] Configure firewall rules (restrict DB access)
- [ ] Enable database backups (daily recommended)
- [ ] Set up monitoring and logging
- [ ] Configure CORS for frontend domain
- [ ] Enable database audit logging

## Backing Up Production Data

```bash
# Backup
pg_dump -U bead_user -h db.example.com bead > backup-$(date +%Y%m%d).sql

# Restore
psql -U bead_user -h db.example.com bead < backup-20260320.sql
```
