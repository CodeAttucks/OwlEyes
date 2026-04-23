# Staging Validation Report Edge Function

Receives CI staging security reports and stores them in Supabase.

## Security model

- Requires `Authorization: Bearer <EDGE_FUNCTION_TOKEN>` header.
- Rejects non-POST methods.
- Logs structured events for auth failures, payload validation, persistence failures, and accepted reports.
- Uses `SUPABASE_SERVICE_ROLE_KEY` only inside the function runtime to write to `security_validation_reports`.

## Required function secrets

Set these before deploying:

```bash
supabase secrets set \
  EDGE_FUNCTION_TOKEN="your-long-random-token" \
  SUPABASE_URL="https://<project-ref>.supabase.co" \
  SUPABASE_SERVICE_ROLE_KEY="<service-role-key>"
```

## Deploy

```bash
supabase functions deploy staging-validation-report --no-verify-jwt
```

`--no-verify-jwt` is used here because CI calls the function with a machine token (`EDGE_FUNCTION_TOKEN`) rather than a user JWT.

## GitHub Actions Auto-Deploy

The repository includes an automatic deployment workflow at `.github/workflows/deploy-edge-function.yml`.

It deploys on push to `main`, but only after GitHub Environment protection checks pass.

Create a GitHub Environment named `supabase-production` and configure protection rules:

- Required reviewers (recommended)
- Wait timer (optional)
- Deployment branch restriction to `main` (recommended)

Add these Environment secrets to `supabase-production`:

- `SUPABASE_ACCESS_TOKEN`
- `SUPABASE_PROJECT_REF`
- `EDGE_FUNCTION_TOKEN`
- `SUPABASE_SERVICE_ROLE_KEY`
- `STAGING_VALIDATION_EDGE_URL` (used for environment URL display)

## Test

```bash
curl -X POST "https://<project-ref>.functions.supabase.co/staging-validation-report" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <EDGE_FUNCTION_TOKEN>" \
  -d '{
    "repository":"CodeAttucks/OwlEyes",
    "pull_request_number":123,
    "sha":"abc123",
    "run_id":"987654321",
    "run_url":"https://github.com/CodeAttucks/OwlEyes/actions/runs/987654321",
    "report":"Summary: PASS=10 FAIL=0 WARN=1"
  }'
```
