#!/bin/bash

# Production Deployment Script for BEAD Platform
# This script handles production deployment with proper checks and backups

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 BEAD Platform Production Deployment${NC}"
echo "========================================"

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not installed${NC}"
    exit 1
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose not installed${NC}"
    exit 1
fi

# Check .env file
if [ ! -f .env ]; then
    echo -e "${RED}❌ .env file not found${NC}"
    echo "Please copy .env.production.example to .env and configure it"
    exit 1
fi

echo -e "${GREEN}✅ Prerequisites checked${NC}"

# Load environment
set -a
source .env
set +a

# Backup current database
echo -e "${YELLOW}📦 Creating database backup...${NC}"
BACKUP_DIR="./backups"
mkdir -p "$BACKUP_DIR"
BACKUP_FILE="$BACKUP_DIR/bead_backup_$(date +%Y%m%d_%H%M%S).sql"

# If using local database in containers
if docker-compose -f docker-compose.prod.yml ps db 2>/dev/null | grep -q "db"; then
    docker-compose -f docker-compose.prod.yml exec -T db pg_dump -U postgres bead > "$BACKUP_FILE" && \
    echo -e "${GREEN}✅ Backup created: $BACKUP_FILE${NC}" || \
    echo -e "${YELLOW}⚠️  Backup creation skipped${NC}"
fi

# Stop existing services
echo -e "${YELLOW}🛑 Stopping existing services...${NC}"
docker-compose -f docker-compose.prod.yml down || true

# Build images
echo -e "${YELLOW}🏗️  Building Docker images...${NC}"
docker-compose -f docker-compose.prod.yml build --no-cache

# Start services
echo -e "${YELLOW}🚀 Starting services...${NC}"
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to be healthy
echo -e "${YELLOW}⏳ Waiting for services to become healthy...${NC}"
sleep 15

# Check service status
echo -e "${YELLOW}🔍 Checking service status...${NC}"
docker-compose -f docker-compose.prod.yml ps

# Verify database connectivity
echo -e "${YELLOW}🗄️  Verifying database connectivity...${NC}"
if docker-compose -f docker-compose.prod.yml exec -T db psql -U postgres -d bead -c "SELECT version();" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Database connection successful${NC}"
else
    echo -e "${RED}❌ Database connection failed${NC}"
    exit 1
fi

# Run migrations if needed
echo -e "${YELLOW}📝 Running database migrations...${NC}"
docker-compose -f docker-compose.prod.yml exec -T api python -m alembic upgrade head || true

# Health checks
echo -e "${YELLOW}🏥 Running health checks...${NC}"

API_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health || echo "000")
if [ "$API_HEALTH" = "200" ]; then
    echo -e "${GREEN}✅ API is healthy${NC}"
else
    echo -e "${YELLOW}⚠️  API health check returned: $API_HEALTH${NC}"
fi

WEB_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 || echo "000")
if [ "$WEB_HEALTH" = "200" ] || [ "$WEB_HEALTH" = "302" ]; then
    echo -e "${GREEN}✅ Web is healthy${NC}"
else
    echo -e "${YELLOW}⚠️  Web health check returned: $WEB_HEALTH${NC}"
fi

# SSL certificate provisioning
echo -e "${YELLOW}🔒 Checking SSL certificate...${NC}"
DOMAIN="bead-it.org"
CERT_PATH="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"

if [ ! -f "$CERT_PATH" ]; then
    echo -e "${YELLOW}⚠️  SSL certificate not found. Provisioning with certbot...${NC}"

    if ! command -v certbot &> /dev/null; then
        echo -e "${YELLOW}Installing certbot...${NC}"
        sudo apt-get update -qq && sudo apt-get install -y certbot python3-certbot-nginx
    fi

    # Stop nginx container temporarily so certbot can use port 80
    docker-compose -f docker-compose.prod.yml stop nginx || true

    sudo certbot certonly --standalone \
        -d "$DOMAIN" -d "www.$DOMAIN" \
        --non-interactive --agree-tos \
        --email "${CERTBOT_EMAIL:-admin@bead-it.org}" \
        --expand

    # Set up auto-renewal cron job if not already present
    if ! sudo crontab -l 2>/dev/null | grep -q "certbot renew"; then
        (sudo crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet --deploy-hook 'docker exec \$(docker ps -qf name=nginx) nginx -s reload'") | sudo crontab -
        echo -e "${GREEN}✅ Certbot auto-renewal cron job configured${NC}"
    fi

    # Restart nginx with the new certificate
    docker-compose -f docker-compose.prod.yml start nginx
    echo -e "${GREEN}✅ SSL certificate provisioned for $DOMAIN${NC}"
else
    echo -e "${GREEN}✅ SSL certificate already present at $CERT_PATH${NC}"
fi

echo ""
echo -e "${GREEN}✅ Production deployment complete!${NC}"
echo ""
echo "Service URLs:"
echo "  - API (internal):  http://localhost:8000"
echo "  - Web (internal):  http://localhost:3000"
echo "  - Public HTTPS:    https://bead-it.org"
echo "  - Public HTTPS:    https://www.bead-it.org"
echo ""
echo "DNS records required (set at your registrar):"
echo "  A     bead-it.org      ->  <your-server-public-ip>"
echo "  A     www.bead-it.org  ->  <your-server-public-ip>"
echo ""
echo "Firewall rules required:"
echo "  sudo ufw allow 80/tcp"
echo "  sudo ufw allow 443/tcp"
echo "  sudo ufw deny 8000/tcp"
echo "  sudo ufw deny 3000/tcp"
echo "  sudo ufw deny 5432/tcp"
echo "  4. Set up monitoring and backups"
echo ""
