#!/usr/bin/env bash
set -euo pipefail

# Provisions Azure PostgreSQL Flexible Server and imports schema/data for BEAD.
# Required environment variables:
#   RESOURCE_GROUP, LOCATION, POSTGRES_SERVER, POSTGRES_DB,
#   POSTGRES_ADMIN_USER
# Sensitive values (can be provided directly or loaded from Key Vault):
#   POSTGRES_ADMIN_PASSWORD
# Optional Key Vault support:
#   KEY_VAULT_NAME
#   POSTGRES_ADMIN_PASSWORD_SECRET_NAME (default: POSTGRES_ADMIN_PASSWORD)
# Optional:
#   POSTGRES_SKU (default: Standard_B1ms)

required_vars=(
  RESOURCE_GROUP
  LOCATION
  POSTGRES_SERVER
  POSTGRES_DB
  POSTGRES_ADMIN_USER
)

for v in "${required_vars[@]}"; do
  if [[ -z "${!v:-}" ]]; then
    echo "Missing required environment variable: $v" >&2
    exit 1
  fi
done

if ! command -v az >/dev/null 2>&1; then
  echo "Azure CLI (az) is required." >&2
  exit 1
fi

if ! command -v psql >/dev/null 2>&1; then
  echo "psql is required to enable extensions and import schema." >&2
  exit 1
fi

if ! az account show >/dev/null 2>&1; then
  echo "You are not logged in to Azure CLI. Run: az login" >&2
  exit 1
fi

resolve_secret_var() {
  local var_name="$1"
  local secret_name_var="$2"
  local default_secret_name="$3"

  if [[ -n "${!var_name:-}" ]]; then
    return
  fi

  if [[ -z "${KEY_VAULT_NAME:-}" ]]; then
    echo "Missing required environment variable: $var_name" >&2
    echo "Set $var_name directly or provide KEY_VAULT_NAME and an accessible secret." >&2
    exit 1
  fi

  local configured_secret_name="${!secret_name_var:-}"
  local secret_name="${configured_secret_name:-$default_secret_name}"
  local secret_value

  secret_value="$(az keyvault secret show --vault-name "$KEY_VAULT_NAME" --name "$secret_name" --query value -o tsv 2>/dev/null || true)"
  if [[ -z "$secret_value" ]]; then
    echo "Missing secret '$secret_name' in Key Vault '$KEY_VAULT_NAME' for $var_name" >&2
    exit 1
  fi

  export "$var_name=$secret_value"
}

resolve_secret_var "POSTGRES_ADMIN_PASSWORD" "POSTGRES_ADMIN_PASSWORD_SECRET_NAME" "POSTGRES_ADMIN_PASSWORD"

POSTGRES_SKU="${POSTGRES_SKU:-Standard_B1ms}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Creating resource group: $RESOURCE_GROUP"
az group create \
  --name "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --output none

echo "Creating PostgreSQL Flexible Server: $POSTGRES_SERVER"
az postgres flexible-server create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$POSTGRES_SERVER" \
  --location "$LOCATION" \
  --admin-user "$POSTGRES_ADMIN_USER" \
  --admin-password "$POSTGRES_ADMIN_PASSWORD" \
  --sku-name "$POSTGRES_SKU" \
  --tier Burstable \
  --storage-size 32 \
  --version 15 \
  --yes \
  --output none

CURRENT_IP="$(curl -s https://api.ipify.org)"
if [[ -n "$CURRENT_IP" ]]; then
  echo "Adding temporary firewall rule for current IP: $CURRENT_IP"
  az postgres flexible-server firewall-rule create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$POSTGRES_SERVER" \
    --rule-name "allow-local-ip" \
    --start-ip-address "$CURRENT_IP" \
    --end-ip-address "$CURRENT_IP" \
    --output none
fi

echo "Creating database: $POSTGRES_DB"
az postgres flexible-server db create \
  --resource-group "$RESOURCE_GROUP" \
  --server-name "$POSTGRES_SERVER" \
  --database-name "$POSTGRES_DB" \
  --output none

PG_FQDN="$(az postgres flexible-server show --resource-group "$RESOURCE_GROUP" --name "$POSTGRES_SERVER" --query fullyQualifiedDomainName -o tsv)"
DB_USER_FQ="${POSTGRES_ADMIN_USER}@${POSTGRES_SERVER}"

PSQL_CONN="host=$PG_FQDN port=5432 dbname=$POSTGRES_DB user=$DB_USER_FQ sslmode=require"

echo "Enabling PostGIS extensions"
PGPASSWORD="$POSTGRES_ADMIN_PASSWORD" psql "$PSQL_CONN" -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS postgis;"
PGPASSWORD="$POSTGRES_ADMIN_PASSWORD" psql "$PSQL_CONN" -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS postgis_topology;"

echo "Importing schema, views, and seed data"
for sql_file in "$ROOT_DIR/db/schema.sql" "$ROOT_DIR/db/views.sql" "$ROOT_DIR/db/seed.sql"; do
  if [[ -f "$sql_file" ]]; then
    echo "Applying $(basename "$sql_file")"
    PGPASSWORD="$POSTGRES_ADMIN_PASSWORD" psql "$PSQL_CONN" -v ON_ERROR_STOP=1 -f "$sql_file"
  else
    echo "Skipping missing file: $sql_file"
  fi
done

DB_USER_URL="${POSTGRES_ADMIN_USER}%40${POSTGRES_SERVER}"
DATABASE_URL="postgresql://${DB_USER_URL}:${POSTGRES_ADMIN_PASSWORD}@${PG_FQDN}:5432/${POSTGRES_DB}?sslmode=require"

echo ""
echo "PostgreSQL provisioning complete."
echo "DATABASE_URL=$DATABASE_URL"
