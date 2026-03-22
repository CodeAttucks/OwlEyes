#!/usr/bin/env bash
set -euo pipefail

# Rotates app secrets and updates Azure Key Vault.
# Required:
#   KEY_VAULT_NAME
# Optional:
#   SECRET_KEY_SECRET_NAME (default: SECRET_KEY)
#   POSTGRES_ADMIN_PASSWORD_SECRET_NAME (default: POSTGRES_ADMIN_PASSWORD)
#   BASE44_API_KEY_SECRET_NAME (default: BASE44_API_KEY)
#   AZURE_OPENAI_API_KEY_SECRET_NAME (default: AZURE_OPENAI_API_KEY)
#
# Optional values to set directly (recommended for externally rotated provider keys):
#   BASE44_API_KEY
#   AZURE_OPENAI_API_KEY
#
# Optional PostgreSQL admin password rotation:
#   RESOURCE_GROUP
#   POSTGRES_SERVER
#   ROTATE_POSTGRES_ADMIN_PASSWORD=true

if [[ -z "${KEY_VAULT_NAME:-}" ]]; then
  echo "Missing required environment variable: KEY_VAULT_NAME" >&2
  exit 1
fi

if ! command -v az >/dev/null 2>&1; then
  echo "Azure CLI (az) is required." >&2
  exit 1
fi

if ! az account show >/dev/null 2>&1; then
  echo "You are not logged in to Azure CLI. Run: az login" >&2
  exit 1
fi

SECRET_KEY_SECRET_NAME="${SECRET_KEY_SECRET_NAME:-SECRET_KEY}"
POSTGRES_ADMIN_PASSWORD_SECRET_NAME="${POSTGRES_ADMIN_PASSWORD_SECRET_NAME:-POSTGRES_ADMIN_PASSWORD}"
BASE44_API_KEY_SECRET_NAME="${BASE44_API_KEY_SECRET_NAME:-BASE44_API_KEY}"
AZURE_OPENAI_API_KEY_SECRET_NAME="${AZURE_OPENAI_API_KEY_SECRET_NAME:-AZURE_OPENAI_API_KEY}"

generate_secret() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -base64 48 | tr -d '\n'
  else
    # Fallback if openssl is unavailable.
    date +%s%N | sha256sum | awk '{print $1}'
  fi
}

set_kv_secret() {
  local name="$1"
  local value="$2"
  az keyvault secret set \
    --vault-name "$KEY_VAULT_NAME" \
    --name "$name" \
    --value "$value" \
    --output none
}

NEW_SECRET_KEY="$(generate_secret)"
NEW_POSTGRES_ADMIN_PASSWORD="$(generate_secret)"

echo "Updating Key Vault secret: $SECRET_KEY_SECRET_NAME"
set_kv_secret "$SECRET_KEY_SECRET_NAME" "$NEW_SECRET_KEY"

echo "Updating Key Vault secret: $POSTGRES_ADMIN_PASSWORD_SECRET_NAME"
set_kv_secret "$POSTGRES_ADMIN_PASSWORD_SECRET_NAME" "$NEW_POSTGRES_ADMIN_PASSWORD"

if [[ "${ROTATE_POSTGRES_ADMIN_PASSWORD:-false}" == "true" ]]; then
  if [[ -z "${RESOURCE_GROUP:-}" || -z "${POSTGRES_SERVER:-}" ]]; then
    echo "To rotate PostgreSQL server password, set RESOURCE_GROUP and POSTGRES_SERVER." >&2
    exit 1
  fi

  echo "Rotating PostgreSQL Flexible Server admin password"
  az postgres flexible-server update \
    --resource-group "$RESOURCE_GROUP" \
    --name "$POSTGRES_SERVER" \
    --admin-password "$NEW_POSTGRES_ADMIN_PASSWORD" \
    --output none
fi

if [[ -n "${BASE44_API_KEY:-}" ]]; then
  echo "Updating Key Vault secret: $BASE44_API_KEY_SECRET_NAME"
  set_kv_secret "$BASE44_API_KEY_SECRET_NAME" "$BASE44_API_KEY"
else
  echo "Skipping $BASE44_API_KEY_SECRET_NAME (BASE44_API_KEY not provided)."
fi

if [[ -n "${AZURE_OPENAI_API_KEY:-}" ]]; then
  echo "Updating Key Vault secret: $AZURE_OPENAI_API_KEY_SECRET_NAME"
  set_kv_secret "$AZURE_OPENAI_API_KEY_SECRET_NAME" "$AZURE_OPENAI_API_KEY"
else
  echo "Skipping $AZURE_OPENAI_API_KEY_SECRET_NAME (AZURE_OPENAI_API_KEY not provided)."
fi

echo ""
echo "Secret rotation complete."
echo "Redeploy API to apply updated secrets."
