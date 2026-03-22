#!/usr/bin/env bash
set -euo pipefail

# Builds/pushes API image to ACR and deploys it to Azure App Service.
# Required environment variables:
#   RESOURCE_GROUP, LOCATION, APP_SERVICE_PLAN, APP_SERVICE_NAME,
#   ACR_NAME, POSTGRES_SERVER, POSTGRES_DB, POSTGRES_ADMIN_USER
# Sensitive values (can be provided directly or loaded from Key Vault):
#   POSTGRES_ADMIN_PASSWORD, SECRET_KEY,
#   AZURE_AD_TENANT_ID, AZURE_AD_CLIENT_ID, AZURE_AD_AUDIENCE
# Optional Key Vault support:
#   KEY_VAULT_NAME
#   POSTGRES_ADMIN_PASSWORD_SECRET_NAME (default: POSTGRES_ADMIN_PASSWORD)
#   SECRET_KEY_SECRET_NAME (default: SECRET_KEY)
#   AZURE_AD_TENANT_ID_SECRET_NAME (default: AZURE_AD_TENANT_ID)
#   AZURE_AD_CLIENT_ID_SECRET_NAME (default: AZURE_AD_CLIENT_ID)
#   AZURE_AD_AUDIENCE_SECRET_NAME (default: AZURE_AD_AUDIENCE)
# Optional:
#   API_IMAGE_NAME (default: bead-api)

required_vars=(
  RESOURCE_GROUP
  LOCATION
  APP_SERVICE_PLAN
  APP_SERVICE_NAME
  ACR_NAME
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
resolve_secret_var "SECRET_KEY" "SECRET_KEY_SECRET_NAME" "SECRET_KEY"
resolve_secret_var "AZURE_AD_TENANT_ID" "AZURE_AD_TENANT_ID_SECRET_NAME" "AZURE_AD_TENANT_ID"
resolve_secret_var "AZURE_AD_CLIENT_ID" "AZURE_AD_CLIENT_ID_SECRET_NAME" "AZURE_AD_CLIENT_ID"
resolve_secret_var "AZURE_AD_AUDIENCE" "AZURE_AD_AUDIENCE_SECRET_NAME" "AZURE_AD_AUDIENCE"

API_IMAGE_NAME="${API_IMAGE_NAME:-bead-api}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

echo "Ensuring resource group exists: $RESOURCE_GROUP"
az group create \
  --name "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --output none

echo "Ensuring App Service plan exists: $APP_SERVICE_PLAN"
az appservice plan create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$APP_SERVICE_PLAN" \
  --location "$LOCATION" \
  --is-linux \
  --sku B1 \
  --output none

echo "Ensuring ACR exists: $ACR_NAME"
az acr create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$ACR_NAME" \
  --sku Basic \
  --admin-enabled true \
  --output none || true

IMAGE_TAG="$(git rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M%S)"
echo "Building API image in ACR with tag: $IMAGE_TAG"
az acr build \
  --registry "$ACR_NAME" \
  --image "$API_IMAGE_NAME:$IMAGE_TAG" \
  --file Dockerfile.api \
  . \
  --output none

ACR_LOGIN_SERVER="$(az acr show --resource-group "$RESOURCE_GROUP" --name "$ACR_NAME" --query loginServer -o tsv)"
ACR_USER="$(az acr credential show --resource-group "$RESOURCE_GROUP" --name "$ACR_NAME" --query username -o tsv)"
ACR_PASS="$(az acr credential show --resource-group "$RESOURCE_GROUP" --name "$ACR_NAME" --query passwords[0].value -o tsv)"
IMAGE_URI="${ACR_LOGIN_SERVER}/${API_IMAGE_NAME}:${IMAGE_TAG}"

echo "Ensuring App Service exists: $APP_SERVICE_NAME"
if ! az webapp show --resource-group "$RESOURCE_GROUP" --name "$APP_SERVICE_NAME" >/dev/null 2>&1; then
  az webapp create \
    --resource-group "$RESOURCE_GROUP" \
    --plan "$APP_SERVICE_PLAN" \
    --name "$APP_SERVICE_NAME" \
    --deployment-container-image-name "$IMAGE_URI" \
    --output none
fi

echo "Configuring App Service container settings"
az webapp config container set \
  --resource-group "$RESOURCE_GROUP" \
  --name "$APP_SERVICE_NAME" \
  --docker-custom-image-name "$IMAGE_URI" \
  --docker-registry-server-url "https://$ACR_LOGIN_SERVER" \
  --docker-registry-server-user "$ACR_USER" \
  --docker-registry-server-password "$ACR_PASS" \
  --output none

PG_FQDN="$(az postgres flexible-server show --resource-group "$RESOURCE_GROUP" --name "$POSTGRES_SERVER" --query fullyQualifiedDomainName -o tsv)"
DB_USER_URL="${POSTGRES_ADMIN_USER}%40${POSTGRES_SERVER}"
DATABASE_URL="postgresql://${DB_USER_URL}:${POSTGRES_ADMIN_PASSWORD}@${PG_FQDN}:5432/${POSTGRES_DB}?sslmode=require"
AZURE_AD_ISSUER="${AZURE_AD_ISSUER:-https://login.microsoftonline.com/${AZURE_AD_TENANT_ID}/v2.0}"
AZURE_AD_OPENID_CONFIG_URL="${AZURE_AD_OPENID_CONFIG_URL:-https://login.microsoftonline.com/${AZURE_AD_TENANT_ID}/v2.0/.well-known/openid-configuration}"

echo "Applying API app settings"
az webapp config appsettings set \
  --resource-group "$RESOURCE_GROUP" \
  --name "$APP_SERVICE_NAME" \
  --settings \
    WEBSITES_PORT=8000 \
    PORT=8000 \
    DATABASE_URL="$DATABASE_URL" \
    SECRET_KEY="$SECRET_KEY" \
    AUTH_ENABLED=true \
    AZURE_AD_TENANT_ID="$AZURE_AD_TENANT_ID" \
    AZURE_AD_CLIENT_ID="$AZURE_AD_CLIENT_ID" \
    AZURE_AD_AUDIENCE="$AZURE_AD_AUDIENCE" \
    AZURE_AD_ISSUER="$AZURE_AD_ISSUER" \
    AZURE_AD_OPENID_CONFIG_URL="$AZURE_AD_OPENID_CONFIG_URL" \
  --output none

echo "Allowing App Service outbound IPs in PostgreSQL firewall"
OUTBOUND_IPS="$(az webapp show --resource-group "$RESOURCE_GROUP" --name "$APP_SERVICE_NAME" --query outboundIpAddresses -o tsv)"
IFS=',' read -r -a ip_array <<< "$OUTBOUND_IPS"
for i in "${!ip_array[@]}"; do
  ip="${ip_array[$i]}"
  [[ -z "$ip" ]] && continue
  az postgres flexible-server firewall-rule create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$POSTGRES_SERVER" \
    --rule-name "allow-appsvc-$i" \
    --start-ip-address "$ip" \
    --end-ip-address "$ip" \
    --output none
 done

echo "Restarting App Service"
az webapp restart \
  --resource-group "$RESOURCE_GROUP" \
  --name "$APP_SERVICE_NAME" \
  --output none

APP_URL="https://${APP_SERVICE_NAME}.azurewebsites.net"
echo ""
echo "API deployment complete."
echo "App URL: $APP_URL"
echo "Health endpoint: $APP_URL/health"
