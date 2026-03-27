# Welcome to BEAD_IT!

An all-in-one program management dashboard for tracking BEAD-funded electrical and broadband infrastructure projects, from supply chain and vendor compliance to environmental permitting.

Project space: https://beadit.atlassian.net/wiki/spaces/KAN/pages/524289/What+is+BEAD_IT

## 🔐 Security & Environment Setup

**⚠️ IMPORTANT:** Never commit sensitive credentials to version control.

- **[GITHUB_SECRETS_SETUP.md](GITHUB_SECRETS_SETUP.md)** — Comprehensive guide for setting up GitHub & Supabase environment secrets
- **[CREDENTIAL_ROTATION.md](CREDENTIAL_ROTATION.md)** — How to handle exposed credentials and rotate keys
- **[bead-platform/.env.example](bead-platform/.env.example)** — Backend environment variables template
- **[bead-platform/.env.production.example](bead-platform/.env.production.example)** — Production environment template

All `.env`, `.env.*` (except `.env.example`), and sensitive files are protected by `.gitignore`.

## Admin Inspector (Supabase)

Use the local admin script for read-only inspection tasks such as listing users and checking auth settings.

```bash
SUPABASE_URL=${{ secrets.SUPABASE_URL }} \
SUPABASE_SERVICE_ROLE_KEY=${{ secrets.SUPABASE_SERVICE_ROLE_KEY }} \
node admin_Inspector.js list-users

SUPABASE_URL=${{ secrets.SUPABASE_URL }} \
SUPABASE_SERVICE_ROLE_KEY=${{ secrets.SUPABASE_SERVICE_ROLE_KEY }} \
node admin_Inspector.js auth-settings
```