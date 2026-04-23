# 🔐 Credential Exposure Response Guide

## Exposed Credential Summary

A Supabase **publishable/anon key** was accidentally exposed:
```
sb_publishable_KCIF4MY_KWhI947PtnAPYg__AXV6tYa
```

**Risk Level:** 🟡 **MEDIUM**
- **Good news:** This is an anon/public key (frontend-safe, limited permissions)
- **Action:** Regenerate immediately as precaution; monitor for abuse

---

## Immediate Actions (Do These Now)

### Step 1: Revoke Exposed Key in Supabase (2 mins)

1. Go to [Supabase Dashboard](https://app.supabase.com)
2. Select your project
3. **Settings → API**
4. Under "Anon/public key" section:
   - Copy the current key shown
   - Click the **"Regenerate"** button next to it
   - ✅ Old key is now revoked, new key is issued

### Step 2: Generate New Tokens (1 min)

Generate two independent random tokens for GitHub:

```bash
# Run these in your terminal to generate secure tokens:
TOKEN_1=$(openssl rand -hex 32)
TOKEN_2=$(openssl rand -hex 32)

echo "STAGING_VALIDATION_EDGE_TOKEN: $TOKEN_1"
echo "EDGE_FUNCTION_TOKEN: $TOKEN_2"
```

Save the output for the next step.

### Step 3: Update GitHub Secrets (3 mins)

Update both repository-level and environment-scoped secrets:

**Repository → Settings → Secrets and variables → Actions**

#### Repository Secrets (update these):
- `STAGING_VALIDATION_EDGE_URL` → Keep same (it's just the URL)
- `STAGING_VALIDATION_EDGE_TOKEN` → `<TOKEN_1 from step 2>`

#### Environment: `supabase-production` → Secrets (update these):
- `SUPABASE_ACCESS_TOKEN` → No change (unless also exposed)
- `SUPABASE_PROJECT_REF` → No change (it's just a reference)
- `EDGE_FUNCTION_TOKEN` → `<TOKEN_2 from step 2>`
- `SUPABASE_SERVICE_ROLE_KEY` → No change (different credential type)

### Step 4: Update Local Development (1 min)

Update your local `.env.local` with the new anon key from Step 1:

```bash
cd /workspaces/OwlEyes/bead-platform/web

# Edit .env.local:
# NEXT_PUBLIC_SUPABASE_ANON_KEY=<NEW_KEY_FROM_STEP_1>
```

Do the same for backend `.env`:
```bash
# Edit /workspaces/OwlEyes/bead-platform/.env:
# NEXT_PUBLIC_SUPABASE_ANON_KEY=<NEW_KEY_FROM_STEP_1>
```

**Do NOT commit these files** — they're in `.gitignore`.

### Step 5: Re-Deploy (2 mins)

Push a commit to `main` to trigger re-deployment with new secrets:

```bash
# Or manually trigger the deploy workflow:
# GitHub → Actions → Deploy Edge Function → Run workflow
```

The deploy workflow will:
1. Pull the new `EDGE_FUNCTION_TOKEN` from secrets
2. Push it to Supabase function environment
3. Redeploy the Edge Function with new auth

---

## Verification (After Deploy)

### ✅ Check PR Validation Still Works

Create a test PR to `main` and verify:
1. PR validation workflow runs
2. Can successfully post to Edge Function (check logs)
3. Artifact upload succeeds

### ✅ Check Edge Function Responds

```bash
# Export your new token
NEW_TOKEN="<TOKEN_2_from_step_2>"
PROJECT_REF="your-project-ref"

# Test the endpoint
curl -X POST \
  https://${PROJECT_REF}.supabase.co/functions/v1/staging-validation-report \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${NEW_TOKEN}" \
  -d '{
    "repository": "CodeAttucks/OwlEyes",
    "pull_request_number": 999,
    "sha": "test123",
    "run_id": "test456",
    "run_url": "https://github.com/.../actions/runs/test456",
    "report": "# Test Report\n\nRotation successful."
  }'
```

Expected response:
```json
{
  "ok": true,
  "request_id": "uuid-here"
}
```

### ✅ Check Edge Function Logs

In Supabase dashboard:
- **Functions → staging-validation-report → Logs**
- Should see successful requests with new token
- Should see auth failures if old token is used (good sign it's revoked)

---

## Security Audit

### Questions to Ask

- [ ] Was the exposed key ever checked into git history? 
  - If yes: Run `git filter-branch` or `BFG Repo-Cleaner` to remove from history
- [ ] Are database row-level security (RLS) policies in place?
  - If no: Edge Function should only insert, not read unfiltered data
- [ ] Are API request logs available?
  - Check Supabase → Logs → Edge Functions for any unauthorized access during exposure window
- [ ] Is rate-limiting configured?
  - Helps mitigate abuse if key is used maliciously

### Run This Check

```bash
# Make sure exposed key is NOT in current codebase
grep -r "sb_publishable_KCIF4MY_KWhI947PtnAPYg__AXV6tYa" /workspaces/OwlEyes/ 2>/dev/null || echo "✅ Not found in codebase"

# Check git history (expensive, but thorough)
cd /workspaces/OwlEyes
git log --all --oneline | wc -l  # How many commits to scan?
git log -p --all -S "sb_publishable_KCIF4MY_KWhI947PtnAPYg__AXV6tYa" -- bead-platform/  # Search history

# If found in history, use:
# git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch FILE' -- --all
# git push origin --force --all
```

---

## Timeline

| Time | Action | ✅ |
|------|--------|-----|
| T+0 | **IMMEDIATELY:** Regenerate Supabase anon key | [ ] |
| T+1 | Generate new GitHub tokens | [ ] |
| T+2 | Update GitHub Secrets (repo + environment) | [ ] |
| T+3 | Update local `.env.local` files | [ ] |
| T+4 | Trigger deploy workflow | [ ] |
| T+5 | Verify Edge Function with new token | [ ] |
| T+10 | Review logs for unauthorized access | [ ] |
| T+60 | Team announcement/sync | [ ] |

**Target Total Time:** ~10 minutes for full rotation

---

## Git History Check (If Committed)

If the exposed key was accidentally committed:

```bash
# 1. Remove the specific file from history (recommended)
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch bead-platform/web/.env.local' \
  -- --all

# 2. Force push to clean up remote
git push origin --force --all

# 3. Notify team to re-clone or fetch pruned history
git fetch --all --prune

# 4. Re-add the file to .gitignore (should already be there)
echo ".env.local" >> .gitignore
git add .gitignore
git commit -m "chore: ensure .env.local never tracked again"
git push origin main
```

⚠️ **Force push is destructive** — only do this if truly necessary and team is aligned.

---

## Long-Term Prevention

### 1. Use `.gitignore` Templates
```bash
# Already in place, verify:
cat bead-platform/.gitignore | grep -E "\.env|secrets?"
```

### 2. Enable Secret Scanning (GitHub)
**Repo → Settings → Security & analysis → Secret scanning**
- Enable "Push protection" (blocks commits with exposed secrets)
- Enable "Secret scanning" (alerts on public repos)

### 3. Add Pre-Commit Hook
```bash
# Create .git/hooks/pre-commit (example):
#!/bin/bash
if git diff --cached | grep -i "^+.*sb_\|^+.*sbp_\|^+.*^api_"; then
  echo "❌ Secret detected in commit. Aborting."
  exit 1
fi
```

### 4. Rotate Keys Regularly
- Personal Access Tokens: Every 90 days
- API Keys: Every 180 days
- Service Role Keys: On rotation cycle or after major changes

### 5. Use Environment Variables Everywhere
```typescript
// ✅ Good
const token = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

// ❌ Bad
const token = "sb_publishable_KCIF4MY_KWhI947PtnAPYg__AXV6tYa";
```

---

## References

- [Supabase - Regenerating API Keys](https://supabase.com/docs/guides/api#managing-api-keys)
- [GitHub - Secret Scanning & Push Protection](https://docs.github.com/en/code-security/secret-scanning)
- [OWASP - Secret Management](https://owasp.org/www-community/Sensitive_Data_Exposure)
- [Git - Removing Sensitive Data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)

---

## Questions?

If you're unsure about any step:
1. Review [GITHUB_SECRETS_SETUP.md](GITHUB_SECRETS_SETUP.md) for context
2. Check Supabase docs for your region/version-specific workflows
3. Test in a non-production environment first
