# GitHub & Supabase Secrets Setup Guide

This document outlines how to securely configure environment secrets for the CI/CD pipeline and Edge Function deployments.

## Security Best Practices

- ⚠️ **NEVER commit credentials** to version control (use `.env`, `.env.local` in `.gitignore`)
- ✅ **Store in GitHub Secrets** for CI/CD workflows (repository or environment-scoped)
- ✅ **Rotate regularly** especially if accidentally exposed
- ✅ **Use the least-privilege principle** - each secret should have minimal required permissions
- ✅ **Environment-scoped secrets** for production workflows (additional approval gates)

---

## 1. Supabase Project Setup

### Get Your Credentials

1. Log into [Supabase Dashboard](https://app.supabase.com)
2. Select your project → **Settings** → **API**
3. Copy:
   - **Project URL** → `SUPABASE_URL`
   - **Anon / public key** → `NEXT_PUBLIC_SUPABASE_ANON_KEY` (✅ safe for frontend)
   - **Service Role key** → `SUPABASE_SERVICE_ROLE_KEY` (⚠️ keep secret, backend/CI only)

4. Go to **Settings** → **Access Tokens** 
5. Create a new Personal Access Token → `SUPABASE_ACCESS_TOKEN` (for CLI deployments)
6. Copy your **Project Ref** (from Project URL or Settings) → `SUPABASE_PROJECT_REF`

---

## 2. GitHub Repository Secrets

### Via GitHub UI:
**Repo → Settings → Secrets and variables → Actions → New repository secret**

### Repository-Level Secrets (accessible in PR workflows)

These are shared across all workflows:

| Secret Name | Value | Purpose | Safe? |
|-------------|-------|---------|-------|
| `STAGING_VALIDATION_EDGE_URL` | `https://<PROJECT_REF>.supabase.co/functions/v1/staging-validation-report` | PR validation webhook endpoint | ✅ |
| `STAGING_VALIDATION_EDGE_TOKEN` | Generated token (see step 3 below) | Bearer token for Edge Function auth | ⚠️ Secret |

**Command to generate STAGING_VALIDATION_EDGE_TOKEN:**
```bash
openssl rand -hex 32  # Generates 64-char hex string like: a3f8d2e9b1c4...
```

---

## 3. GitHub Environment: `supabase-production`

This environment includes approval gates for production deploys.

### Create the Environment:
1. **Repo → Environments → New environment**
2. Name: `supabase-production`
3. **Enable required reviewers** (min 1-2 team members)
4. **Set deployment branches** to `main` only

### Environment-Scoped Secrets:
**Workflow → Environments → supabase-production → Secrets → New secret**

| Secret Name | Value | Purpose |
|-------------|-------|---------|
| `SUPABASE_ACCESS_TOKEN` | Personal Access Token from Supabase | CLI authentication for deployment |
| `SUPABASE_PROJECT_REF` | Project reference ID | Identifies which Supabase project to deploy to |
| `EDGE_FUNCTION_TOKEN` | Generated secret (64-char hex) | Authentication for Edge Function requests |
| `SUPABASE_SERVICE_ROLE_KEY` | Service Role key from API settings | Backend access for Edge Function database operations |

**To generate EDGE_FUNCTION_TOKEN:**
```bash
openssl rand -hex 32
```

---

## 4. Local Development (.env files)

### Backend (.env in bead-platform/)
```bash
# Copy from .env.example and fill in YOUR values
cp bead-platform/.env.example bead-platform/.env

# Edit bead-platform/.env:
DATABASE_URL=postgresql://user:password@localhost:5432/db
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_ROLE_KEY=sbp_...     # From Supabase Settings > API
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbG... # From Supabase Settings > API (anon key)
```

### Frontend (bead-platform/web/.env.local)
```bash
# Already preconfigured, just add Supabase keys:
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbG...  # Public-safe anon key (must start with eyJ or sb_public_)
```

⚠️ **Never commit `.env` or `.env.local`** — both are in `.gitignore`

---

## 5. Workflow-Specific Secret Usage

### PR Validation Workflow (.github/workflows/staging-security-validation.yml)

Uses **repository-level secrets**:
```yaml
env:
  STAGING_VALIDATION_EDGE_URL: ${{ secrets.STAGING_VALIDATION_EDGE_URL }}
  STAGING_VALIDATION_EDGE_TOKEN: ${{ secrets.STAGING_VALIDATION_EDGE_TOKEN }}
```

**When run:** Triggered on pull_request → main

**What it does:**
1. Runs security validator script
2. Uploads report as artifact
3. Posts report to Edge Function (if secrets present)
4. Fails job if validator failed (blocks merge if required)

---

### Deploy Workflow (.github/workflows/deploy-edge-function.yml)

Uses **environment-scoped secrets** (requires approval):
```yaml
jobs:
  deploy-staging-validation-edge-function:
    environment:
      name: supabase-production  # Triggers approval gate
      url: ${{ secrets.STAGING_VALIDATION_EDGE_URL }}
    
    env:
      SUPABASE_ACCESS_TOKEN: ${{ secrets.SUPABASE_ACCESS_TOKEN }}
      SUPABASE_PROJECT_REF: ${{ secrets.SUPABASE_PROJECT_REF }}
      EDGE_FUNCTION_TOKEN: ${{ secrets.EDGE_FUNCTION_TOKEN }}
      SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
```

**When run:** On push to main (after PR approval) or manual dispatch

**What it does:**
1. Pre-deploy smoke check (blocks if validator fails)
2. Validates all secrets are present
3. Pushes secrets to Supabase runtime environment
4. Deploys Edge Function to production

---

## 6. Supabase Function Secrets Runtime

Once deployed, the Edge Function accesses secrets via `Deno.env.get()`:

```typescript
// supabase/functions/staging-validation-report/index.ts
const expectedToken = Deno.env.get("EDGE_FUNCTION_TOKEN");
const supabaseUrl = Deno.env.get("SUPABASE_URL");
const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
```

These are populated by the deploy workflow:
```bash
supabase secrets set \
  EDGE_FUNCTION_TOKEN="<from GitHub>" \
  SUPABASE_URL="<computed from PROJECT_REF>" \
  SUPABASE_SERVICE_ROLE_KEY="<from GitHub>"
```

---

## 7. Credential Rotation Checklist

If a secret is exposed:

- [ ] **Immediate:** Revoke the exposed credential in Supabase Dashboard
- [ ] **Within 5 min:** Generate new token/key
- [ ] **Update GitHub Secrets** with new values
- [ ] **Re-run deploy workflow** to push new secrets to Edge Function
- [ ] **Audit logs:** Check Supabase activity for any unauthorized access
- [ ] **Notify team** of rotation

**For Supabase keys:**
- Personal Access Tokens: **Settings → Access Tokens → Delete**
- Service Role Key: **Settings → API → Regenerate key** (breaks existing deployments until re-deployed)
- Anon Key: Can be regenerated, but update all frontend apps

---

## 8. Deployment Walkthrough

### First-Time Setup:

1. **Generate tokens:**
   ```bash
   # Generate two independent 32-byte hex strings
   openssl rand -hex 32  # For STAGING_VALIDATION_EDGE_TOKEN
   openssl rand -hex 32  # For EDGE_FUNCTION_TOKEN
   ```

2. **Set GitHub repository secrets:**
   - `STAGING_VALIDATION_EDGE_URL` = `https://<PROJECT_REF>.supabase.co/functions/v1/staging-validation-report`
   - `STAGING_VALIDATION_EDGE_TOKEN` = `<first 64-char hex string>`

3. **Create `supabase-production` environment:**
   - Add approval requirements
   - Set deployment branches to `main` only

4. **Set environment secrets:**
   - `SUPABASE_ACCESS_TOKEN` = Your Supabase personal access token
   - `SUPABASE_PROJECT_REF` = Your project reference
   - `EDGE_FUNCTION_TOKEN` = `<second 64-char hex string>`
   - `SUPABASE_SERVICE_ROLE_KEY` = Your service role key from API settings

5. **Push database migration:**
   ```bash
   cd /workspaces/OwlEyes
   supabase login  # Uses SUPABASE_ACCESS_TOKEN
   supabase db push
   ```

6. **Merge PR to main** and monitor deploy workflow:
   - Should trigger approval request on `supabase-production` environment
   - After approval, Edge Function deploys with secrets

7. **Test Edge Function:**
   ```bash
   curl -X POST https://<PROJECT_REF>.supabase.co/functions/v1/staging-validation-report \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <EDGE_FUNCTION_TOKEN>" \
     -d '{
       "repository": "CodeAttucks/OwlEyes",
       "pull_request_number": 123,
       "sha": "abc123...",
       "run_id": "12345",
       "run_url": "https://github.com/.../actions/runs/12345",
       "report": "# Security Validation Report\n\nAll checks passed."
     }'
   ```

---

## 9. Troubleshooting

| Issue | Solution |
|-------|----------|
| "Secret not found in environment" | Check GitHub Secrets name matches workflow reference exactly (case-sensitive) |
| Workflow says "Required approval pending" | Go to Repo → Environments → supabase-production → check approval reviewers |
| Edge Function 401 Unauthorized | Verify `STAGING_VALIDATION_EDGE_TOKEN` matches value in Supabase function environment |
| "supabase db push" fails | Run `supabase login` first, then verify `SUPABASE_ACCESS_TOKEN` has project permissions |
| Precompiled workflow errors | Rerun workflow → Actions → Re-run jobs to refresh secret access |

---

## 10. Security Audit

Run this checklist periodically:

- [ ] No `.env` or `.env.*` files (except `.env.example`) are committed
- [ ] `.gitignore` includes `.env` pattern
- [ ] GitHub Secrets list reviewed for unused/old tokens
- [ ] Service role key only used in backend/CI contexts
- [ ] Anon key used only in frontend contexts (safe to expose)
- [ ] Edge Function logs reviewed for auth failures
- [ ] All deployed functions use `--no-verify-jwt` flag (manual auth via Bearer token)

---

## References

- [Supabase Dashboard](https://app.supabase.com)
- [GitHub Secrets Documentation](https://docs.github.com/en/actions/security-guides/using-secrets-in-github-actions)
- [Supabase Environment Variables](https://supabase.com/docs/guides/functions/secrets)
- [Next.js Environment Variables](https://nextjs.org/docs/basic-features/environment-variables)
