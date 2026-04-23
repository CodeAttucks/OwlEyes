# ✅ Secrets & Environment Setup Checklist

## What's Been Done

### 1. ✅ Environment Files Created/Updated
- [x] `bead-platform/.env.example` → Added `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` variables
- [x] `bead-platform/.env.production.example` → Added Supabase configuration section
- [x] `bead-platform/web/.env.local` → Added Supabase frontend variables (anon key placeholder)
- [x] `.gitignore` → Already protects `.env` and `.env.*` (except templates)

### 2. ✅ Documentation Created
- [x] **[GITHUB_SECRETS_SETUP.md](../GITHUB_SECRETS_SETUP.md)** — Full setup guide for GitHub & Supabase secrets
  - How to get Supabase credentials
  - Repository-level vs environment-scoped secrets
  - Workflow-specific secret usage
  - Local development setup
  - Troubleshooting guide

- [x] **[CREDENTIAL_ROTATION.md](../CREDENTIAL_ROTATION.md)** — Credential rotation & incident response
  - Steps to revoke exposed key
  - Token generation procedures
  - Verification checklist
  - Security audit recommendations
  - Git history cleanup (if needed)

- [x] **[README.md](../README.md)** → Added security section with links

### 3. ✅ CI/CD Workflows Already Configured to Use Secrets
- [x] `.github/workflows/staging-security-validation.yml`
  - Uses: `${{ secrets.STAGING_VALIDATION_EDGE_URL }}`
  - Uses: `${{ secrets.STAGING_VALIDATION_EDGE_TOKEN }}`
  - ✅ Secrets referenced, not hardcoded

- [x] `.github/workflows/deploy-edge-function.yml`
  - Uses: `${{ secrets.SUPABASE_ACCESS_TOKEN }}`
  - Uses: `${{ secrets.SUPABASE_PROJECT_REF }}`
  - Uses: `${{ secrets.EDGE_FUNCTION_TOKEN }}`
  - Uses: `${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}`
  - ✅ All secrets from environment-scoped context (requires approval)

### 4. ✅ Edge Function Ready for Secrets
- [x] `supabase/functions/staging-validation-report/index.ts`
  - Uses: `Deno.env.get("EDGE_FUNCTION_TOKEN")`
  - Uses: `Deno.env.get("SUPABASE_URL")`
  - Uses: `Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")`
  - ✅ Secrets read from runtime environment (set by deploy workflow)

---

## Next Steps (For You to Do)

### 🔴 URGENT: Handle Exposed Credential

The key `sb_publishable_KCIF4MY_KWhI947PtnAPYg__AXV6tYa` needs rotation:

1. **Follow [CREDENTIAL_ROTATION.md](../CREDENTIAL_ROTATION.md)**
   - Takes ~10 minutes
   - Step-by-step instructions provided
   - Includes verification checklist

### 🟡 Required Before Deployment

1. **Generate GitHub Secrets** (see GITHUB_SECRETS_SETUP.md § 1-2)
   ```bash
   # Generate secure tokens:
   openssl rand -hex 32  # STAGING_VALIDATION_EDGE_TOKEN
   openssl rand -hex 32  # EDGE_FUNCTION_TOKEN
   ```

2. **Set up GitHub Environment** (see GITHUB_SECRETS_SETUP.md § 3)
   - Create environment: `supabase-production`
   - Set required approvers
   - Set deployment branch restriction to `main`

3. **Add Environment Secrets to GitHub** (see GITHUB_SECRETS_SETUP.md § 3)
   - `SUPABASE_ACCESS_TOKEN`
   - `SUPABASE_PROJECT_REF`
   - `EDGE_FUNCTION_TOKEN`
   - `SUPABASE_SERVICE_ROLE_KEY`

4. **Set up Local Development** (see GITHUB_SECRETS_SETUP.md § 4)
   - Copy `.env.example` to `.env` and fill in values
   - Copy `.env.local` template and add Supabase anon key

5. **Deploy Database Migration**
   ```bash
   supabase login  # Uses SUPABASE_ACCESS_TOKEN
   supabase db push  # Deploys migration
   ```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   GitHub Actions (CI/CD)                     │
├──────────────────────────┬──────────────────────────────────┤
│                          │                                    │
│  PR Validation           │  Deploy Edge Function             │
│  (Public Secrets)        │  (Environment Secrets + Approval)  │
│                          │                                    │
│  STAGING_VALIDATION_     │  SUPABASE_ACCESS_TOKEN           │
│  EDGE_URL                │  SUPABASE_PROJECT_REF            │
│  STAGING_VALIDATION_     │  EDGE_FUNCTION_TOKEN             │
│  EDGE_TOKEN              │  SUPABASE_SERVICE_ROLE_KEY       │
│                          │                                    │
└──────────────────────────┴──────────────────────────────────┘
                           ↓
            ┌──────────────────────────┐
            │  Supabase Edge Functions  │
            ├──────────────────────────┤
            │ Deno.env.get() reads:     │
            │ - EDGE_FUNCTION_TOKEN    │
            │ - SUPABASE_URL           │
            │ - SUPABASE_SERVICE_ROLE_ │
            │   KEY                    │
            └──────────────────────────┘
                        ↓
            ┌──────────────────────────┐
            │  Supabase PostgreSQL     │
            │  (RLS Protected Table)    │
            └──────────────────────────┘
```

---

## Security Best Practices Implemented

| Practice | Status | Details |
|----------|--------|---------|
| Secrets not in code | ✅ | All hardcoded references removed, using environment variables |
| .env in .gitignore | ✅ | Protected: `.env` and `.env.*` (except templates) |
| Separation of concerns | ✅ | Frontend key (anon) vs backend key (service role) |
| Least privilege | ✅ | Services only get tokens they need |
| Approval gates | ✅ | Deployment requires GitHub Environment approval |
| Audit trails | ✅ | All secrets use Bearer tokens (can be logged) |
| Secret rotation docs | ✅ | CREDENTIAL_ROTATION.md provides procedures |
| Pre-deploy validation | ✅ | Workflow fails if security checks don't pass |

---

## File Dependency Map

```
GITHUB_SECRETS_SETUP.md (reference guide)
├─ Used by: .github/workflows/*.yml
├─ Used by: bead-platform/.env (local)
├─ Used by: bead-platform/web/.env.local (local)
└─ Templates: .env.example, .env.production.example

CREDENTIAL_ROTATION.md (incident response)
├─ If key exposed: → Follow this guide
├─ Expected outcome: New key in GitHub Secrets
└─ Final step: Re-run deploy workflow

.github/workflows/staging-security-validation.yml
├─ References: ${{ secrets.STAGING_VALIDATION_EDGE_URL }}
├─ References: ${{ secrets.STAGING_VALIDATION_EDGE_TOKEN }}
└─ Posts to: supabase/functions/staging-validation-report

.github/workflows/deploy-edge-function.yml
├─ Environment: supabase-production (requires approval)
├─ References: ${{ secrets.SUPABASE_* }}
├─ References: ${{ secrets.EDGE_FUNCTION_TOKEN }}
└─ Deploys: supabase/functions/staging-validation-report

supabase/functions/staging-validation-report/index.ts
├─ Reads: Deno.env.get("EDGE_FUNCTION_TOKEN")
├─ Reads: Deno.env.get("SUPABASE_URL")
├─ Reads: Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")
└─ Auth: Bearer token validation before processing

supabase/migrations/20260322144500_*.sql
└─ Creates: security_validation_reports table (RLS enabled)
```

---

## Commands Quick Reference

### Local Development
```bash
# Set up environment
cp bead-platform/.env.example bead-platform/.env
# Edit .env with your values

cp bead-platform/web/.env.local bead-platform/web/.env.local
# Edit .env.local with Supabase anon key

# Start development server
cd bead-platform/web && npm run dev
```

### Generate Tokens
```bash
# Secure random tokens (use in GitHub Secrets)
openssl rand -hex 32
openssl rand -hex 32
```

### Deploy Infrastructure
```bash
# Push database migration
supabase login
supabase db push

# View Edge Function logs
supabase functions list
supabase functions logs staging-validation-report
```

### Verify Deployment
```bash
# Test Edge Function
curl -X POST https://PROJECT_REF.supabase.co/functions/v1/staging-validation-report \
  -H "Authorization: Bearer <EDGE_FUNCTION_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"repository":"...","pull_request_number":1,...}'
```

---

## Troubleshooting Quick Links

| Problem | Reference |
|---------|-----------|
| Workflow says secrets missing | [GITHUB_SECRETS_SETUP.md § 2-3](../GITHUB_SECRETS_SETUP.md#2-github-repository-secrets) |
| "401 Unauthorized" from Edge Function | [GITHUB_SECRETS_SETUP.md § 9](../GITHUB_SECRETS_SETUP.md#9-troubleshooting) |
| Credential was exposed | [CREDENTIAL_ROTATION.md](../CREDENTIAL_ROTATION.md) |
| Need to rotate keys | [CREDENTIAL_ROTATION.md § Long-Term Prevention](../CREDENTIAL_ROTATION.md#long-term-prevention) |
| Can't deploy Edge Function | Verify `supabase login` worked, check `SUPABASE_ACCESS_TOKEN` permissions |
| Database migration won't push | Run `supabase db pull` first to sync schema, then `supabase db push` |

---

## Status Summary

| Component | Configured | Secure | Documented | Ready |
|-----------|:-----------:|:------:|:-----------:|:-----:|
| GitHub Workflows | ✅ | ✅ | ✅ | ⏳ Secrets needed |
| Edge Function | ✅ | ✅ | ✅ | ⏳ Deploy needed |
| Database | ✅ | ✅ | ✅ | ⏳ Migration needed |
| Environment Files | ✅ | ✅ | ✅ | ✅ |
| .gitignore | ✅ | ✅ | ✅ | ✅ |
| Documentation | ✅ | ✅ | ✅ | ✅ |

**Overall Status:** 🟡 **Blocked on credential management**
- Code is ready (all secrets moved to environment variables)
- Documentation is complete and comprehensive
- **Action required:** Follow CREDENTIAL_ROTATION.md and GITHUB_SECRETS_SETUP.md to activate deployment

---

## Questions?

1. **Security Q&A:** See [GITHUB_SECRETS_SETUP.md § 7-10](../GITHUB_SECRETS_SETUP.md)
2. **Credential emergency:** See [CREDENTIAL_ROTATION.md](../CREDENTIAL_ROTATION.md)
3. **Local development:** See [GITHUB_SECRETS_SETUP.md § 4](../GITHUB_SECRETS_SETUP.md#4-local-development-env-files)
4. **Deployment:** See [GITHUB_SECRETS_SETUP.md § 8](../GITHUB_SECRETS_SETUP.md#8-deployment-walkthrough)
