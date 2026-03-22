# 🚨 EXPEDITED BACKEND SECRET ROTATION

**Exposed Secret:** `sb_secret_<redacted>`  
**Type:** Supabase backend secret (`sb_secret_*`)  
**Risk Level:** 🔴 **CRITICAL** — High permissions, requires immediate rotation  
**Time to Complete:** ~10 minutes  

---

## ✅ Pre-Rotation Verification

- ✅ Secret NOT found in current source files
- ✅ Secret NOT found in git history
- ✅ Secret NOT tracked by version control
- ✅ Safe to rotate immediately (no active deployments to disrupt)

---

## 🔴 STEP 1: REVOKE (2 minutes)

### In Supabase Dashboard

1. Go to **[Supabase Console](https://app.supabase.com)**
2. Select your project
3. **Settings → API**
4. Identify the exposed key:
   - Look for `sb_secret_*` key
   - Check if it matches pattern or is service role/admin token
5. Click **Regenerate** button next to the key
   - ✅ Old key immediately revoked
   - ✅ New key issued automatically
6. **Copy the new key** (you'll need it in step 3)

**What gets revoked:**
- Any requests using old `sb_secret_<redacted>` fail with 401
- Old key cannot access database
- New key has same permissions

---

## 🟡 STEP 2: GENERATE NEW TOKENS (1 minute)

Open terminal and run:

```bash
# Generate secure replacement tokens
TOKEN=$(openssl rand -hex 32)
echo "New EDGE_FUNCTION_TOKEN: $TOKEN"
```

Save this new token for step 3.

---

## 🟢 STEP 3: UPDATE GITHUB SECRETS (3 minutes)

### In GitHub Repository

**Go to:** Repo → Settings → Secrets and variables → Actions

#### Environment `supabase-production`:
1. Click **`supabase-production`** environment
2. Under **Secrets** section:
   - Find `SUPABASE_SERVICE_ROLE_KEY`
   - Click **Update**
   - Paste the newly regenerated key from Supabase dashboard (Step 1)
   - Click **Save**

3. Find `EDGE_FUNCTION_TOKEN`
   - Click **Update**
   - Paste the new token from Step 2
   - Click **Save**

**Other secrets remain unchanged:**
- `SUPABASE_ACCESS_TOKEN` ← Keep as is
- `SUPABASE_PROJECT_REF` ← Keep as is

---

## 📝 STEP 4: UPDATE LOCAL DEV FILES (2 minutes)

```bash
cd /workspaces/OwlEyes/bead-platform

# Update backend .env
nano .env
# Change: SUPABASE_SERVICE_ROLE_KEY=<new_key_from_step_1>

# Update frontend .env
cd web
nano .env.local
# No change needed (uses anon key, not service role)
```

**Do NOT commit these files** (protected by .gitignore)

---

## 🚀 STEP 5: REDEPLOY (2 minutes)

### Trigger Automatic Deployment

**Option A: Via GitHub UI (Recommended)**
```
1. Go to Actions → Deploy Edge Function
2. Click "Run workflow"
3. Branch: main
4. Click green "Run workflow"
5. Wait for deployment to complete (~1-2 min)
6. Check logs for success
```

**Option B: Via Command Line**
```bash
# If Supabase CLI is installed
cd /workspaces/OwlEyes
supabase login
supabase functions deploy staging-validation-report --project-ref YOUR_PROJECT_REF
```

---

## ✅ VERIFICATION (5 minutes)

### Check 1: Edge Function Logs
```
Supabase → Functions → staging-validation-report → Logs

Look for:
✅ Recent successful requests
❌ Any 401 Unauthorized errors (would indicate old token still in use)
```

### Check 2: Test New Credentials
```bash
# Export new token
NEW_TOKEN="<token_from_step_2>"
PROJECT_REF="your-project-ref"

# Test endpoint
curl -X POST \
  https://${PROJECT_REF}.supabase.co/functions/v1/staging-validation-report \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${NEW_TOKEN}" \
  -d '{
    "repository": "CodeAttucks/OwlEyes",
    "pull_request_number": 999,
    "sha": "test",
    "run_id": "test",
    "run_url": "https://github.com/test",
    "report": "Rotation test"
  }'

Expected response:
{
  "ok": true,
  "request_id": "uuid-here"
}
```

### Check 3: Verify PR Validation Still Works
1. Create test PR to `main`
2. Watch staging-security-validation workflow run
3. Should complete successfully with artifact upload

---

## 📊 Timeline Checklist

| Step | Time | Status | ✓ Complete |
|------|------|--------|-----------|
| 1. Revoke key in Supabase | 2 min | 🔴 DO NOW | [ ] |
| 2. Generate new tokens | 1 min | 🔴 DO NOW | [ ] |
| 3. Update GitHub Secrets | 3 min | 🟡 DO NEXT | [ ] |
| 4. Update local .env | 2 min | 🟡 DO NEXT | [ ] |
| 5. Redeploy workflow | 2 min | 🟡 DO NEXT | [ ] |
| 6. Verify logs | 2 min | 🟢 CONFIRM | [ ] |
| 7. Test with new token | 2 min | 🟢 CONFIRM | [ ] |
| **TOTAL** | **~14 min** | | |

---

## 🆘 TROUBLESHOOTING

| Issue | Fix |
|-------|-----|
| "Secret not updated in GitHub" | Refresh page, check environment name spelling (must be exactly `supabase-production`) |
| "Deploy workflow fails" | Check GitHub Secrets are all present, try manual re-run |
| "Edge Function returns 401" | Verify new EDGE_FUNCTION_TOKEN matches what's in GitHub Secrets |
| "Old key still works" | Give Supabase regenerate 1-2 minutes to propagate |
| "Can't log into Supabase CLI" | Check SUPABASE_ACCESS_TOKEN is valid (different from backend secret) |

---

## 🔒 Post-Rotation Security Checklist

After rotation is complete:

- [ ] Old `sb_secret_<redacted>` is revoked (cannot be used)
- [ ] New service role key is in GitHub Secrets
- [ ] New EDGE_FUNCTION_TOKEN is in GitHub Secrets
- [ ] Local .env files updated (not committed)
- [ ] Deploy workflow ran successfully without errors
- [ ] Edge Function logs show successful requests
- [ ] PR validation workflow still posts reports
- [ ] Test endpoint responds with new credentials

---

## 📚 Additional Resources

- Full guide: [CREDENTIAL_ROTATION.md](../CREDENTIAL_ROTATION.md)
- Setup reference: [GITHUB_SECRETS_SETUP.md](../GITHUB_SECRETS_SETUP.md)
- Status dashboard: [SECRETS_SETUP_CHECKLIST.md](../SECRETS_SETUP_CHECKLIST.md)

---

## ⏰ This Message

**Report Generated:** March 22, 2026  
**Rotation Status:** Ready to execute  
**Next Action:** Revoke key in Supabase (Step 1)  
**Estimated Time to Production:** 10-15 minutes
