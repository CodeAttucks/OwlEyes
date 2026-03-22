# Azure Phase 2 and Phase 3 Runbook

This runbook upgrades the current stack to Azure services in two phases.

## Target Stack

- Frontend: Vercel now, Azure Static Web Apps later
- Backend: Azure App Service
- Database: Azure Database for PostgreSQL Flexible Server + PostGIS
- Auth: Azure AD (Microsoft Entra ID)
- Storage: Azure Blob Storage
- Analytics: Power BI
- ETL: Azure Data Factory
- AI: Azure OpenAI

## Phase 2: Upgrade

### Quick Start (Scripted)

Run these from the `bead-platform` directory after `az login`.

1. Provision Azure PostgreSQL Flexible Server and import SQL files:

```bash
export RESOURCE_GROUP=rg-bead-prod
export LOCATION=eastus
export POSTGRES_SERVER=bead-pg-prod
export POSTGRES_DB=bead
export POSTGRES_ADMIN_USER=bead_admin
export POSTGRES_ADMIN_PASSWORD='<strong-password>'

chmod +x scripts/provision-azure-postgres.sh
./scripts/provision-azure-postgres.sh
```

2. Build and deploy API container to App Service:

```bash
export APP_SERVICE_PLAN=asp-bead-prod
export APP_SERVICE_NAME=bead-api-prod
export ACR_NAME=beadacrprod001

# Preferred: resolve sensitive values from Key Vault
export KEY_VAULT_NAME='kv-bead-prod'
export SECRET_KEY_SECRET_NAME='SECRET_KEY'
export POSTGRES_ADMIN_PASSWORD_SECRET_NAME='POSTGRES_ADMIN_PASSWORD'
export AZURE_AD_TENANT_ID_SECRET_NAME='AZURE_AD_TENANT_ID'
export AZURE_AD_CLIENT_ID_SECRET_NAME='AZURE_AD_CLIENT_ID'
export AZURE_AD_AUDIENCE_SECRET_NAME='AZURE_AD_AUDIENCE'

# Optional overrides (if secret names differ from defaults)
# export SECRET_KEY_SECRET_NAME='bead-api-secret-key'
# export AZURE_AD_CLIENT_ID_SECRET_NAME='bead-api-client-id'

# Alternative (fallback): set values directly if not using Key Vault
# export SECRET_KEY='<random-secret>'
# export AZURE_AD_TENANT_ID='<tenant-id>'
# export AZURE_AD_CLIENT_ID='<api-app-client-id>'
# export AZURE_AD_AUDIENCE='api://<api-app-client-id-or-uri>'

chmod +x scripts/deploy-api-appservice.sh
./scripts/deploy-api-appservice.sh
```

3. Validate deployment:

```bash
curl -i "https://${APP_SERVICE_NAME}.azurewebsites.net/health"
```

### 1. Move database to Azure PostgreSQL + PostGIS

1. Create Azure Database for PostgreSQL Flexible Server.
2. Enable required extensions in the target DB:
   - `postgis`
   - `postgis_topology` (optional)
3. Restrict networking to App Service outbound IPs or private endpoint.
4. Import schema and seed data from `db/schema.sql`, `db/views.sql`, `db/seed.sql`.
5. Set `DATABASE_URL` in App Service configuration.

Example URL format:

`postgresql://user:password@server.postgres.database.azure.com:5432/bead?sslmode=require`

### 2. Move API to Azure App Service

1. Create Linux App Service Plan.
2. Create Web App for Containers or Python runtime app.
3. Configure app settings from `.env.production.example`.
4. Deploy from GitHub branch.
5. Validate health and API routes.

Minimum required settings:

- `DATABASE_URL`
- `SECRET_KEY`
- `AUTH_ENABLED=true`
- `AZURE_AD_TENANT_ID`
- `AZURE_AD_CLIENT_ID`
- `AZURE_AD_AUDIENCE`
- `AZURE_AD_ISSUER`
- `AZURE_AD_OPENID_CONFIG_URL`

### Secrets (Key Vault)

The deployment script supports resolving sensitive values from Azure Key Vault.

Use these environment variables before running `scripts/deploy-api-appservice.sh`:

- `KEY_VAULT_NAME`
- `POSTGRES_ADMIN_PASSWORD_SECRET_NAME` (optional, default: `POSTGRES_ADMIN_PASSWORD`)
- `SECRET_KEY_SECRET_NAME` (optional, default: `SECRET_KEY`)
- `AZURE_AD_TENANT_ID_SECRET_NAME` (optional, default: `AZURE_AD_TENANT_ID`)
- `AZURE_AD_CLIENT_ID_SECRET_NAME` (optional, default: `AZURE_AD_CLIENT_ID`)
- `AZURE_AD_AUDIENCE_SECRET_NAME` (optional, default: `AZURE_AD_AUDIENCE`)

If `KEY_VAULT_NAME` is set, the script pulls missing sensitive variables from Key Vault.
If `KEY_VAULT_NAME` is not set, sensitive values must be provided directly as environment variables.

Example:

```bash
export KEY_VAULT_NAME='kv-bead-prod'
export SECRET_KEY_SECRET_NAME='SECRET_KEY'
export AZURE_AD_CLIENT_ID_SECRET_NAME='AZURE_AD_CLIENT_ID'
./scripts/deploy-api-appservice.sh
```

### Rotate Previously Exposed Keys

Any previously exposed secret should be treated as compromised and rotated.

1. Rotate provider-side credentials first:
   - Base44 API key
   - Azure OpenAI API key
   - PostgreSQL admin password (if exposed)
   - App `SECRET_KEY`

2. Update Azure Key Vault values:

```bash
# Example: update values after rotating in source systems
az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name SECRET_KEY --value "<new-secret-key>"
az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name POSTGRES_ADMIN_PASSWORD --value "<new-postgres-admin-password>"
az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name BASE44_API_KEY --value "<new-base44-api-key>"
az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name AZURE_OPENAI_API_KEY --value "<new-azure-openai-key>"
```

3. Redeploy API so new settings are applied:

```bash
./scripts/deploy-api-appservice.sh
```

### 3. Add Azure AD auth

Auth support is implemented in `api/auth.py` and globally attached in `api/main.py`.

Behavior:

- If `AUTH_ENABLED=false`, auth is bypassed (local/dev mode).
- If `AUTH_ENABLED=true`, every API request requires a Bearer token validated against Azure AD JWKS.

Azure AD setup steps:

1. Register backend API app in Entra ID.
2. Set Application ID URI (for audience).
3. Expose at least one API scope.
4. Register frontend app and grant delegated permissions.
5. Acquire access token in frontend and send `Authorization: Bearer <token>` to API.

## Phase 3: Enterprise

### 1. Data Factory

1. Create Data Factory instance.
2. Create linked services:
   - Source systems (FCC/BDC/CSV)
   - Azure PostgreSQL target
   - Blob Storage staging
3. Create pipelines for incremental loads and schedule triggers.
4. Add monitoring alerts on pipeline failures.

### 2. Blob Storage

1. Create Storage Account and private container.
2. Store raw uploads and ETL staging files in Blob.
3. Rotate credentials and use managed identity where possible.
4. Configure:
   - `AZURE_STORAGE_CONNECTION_STRING`
   - `AZURE_STORAGE_CONTAINER`

### 3. Azure OpenAI

1. Create Azure OpenAI resource and deploy model.
2. Configure API settings:
   - `AZURE_OPENAI_ENDPOINT`
   - `AZURE_OPENAI_API_KEY`
   - `AZURE_OPENAI_DEPLOYMENT`
3. Route AI insights service calls through this endpoint.

## Cutover Checklist

- `DATABASE_URL` points to Azure PostgreSQL with `sslmode=require`
- API deployed on App Service and passing health checks
- Azure AD token validation enabled in production
- Frontend calls production API base URL
- Blob storage configured for uploads and ETL staging
- Data Factory pipelines deployed and scheduled
- Azure OpenAI integration tested end-to-end
- Dashboard/reporting validated after data migration

## Rollback Plan

1. Keep old database snapshot until sign-off.
2. Keep old API deployment slot for fast swap-back.
3. Keep `AUTH_ENABLED` flag togglable for emergency disable.
4. Repoint frontend API URL to previous endpoint if needed.
