/**
 * admin_inspector.js
 *
 * Local Node script to perform admin-only tasks against a Supabase project.
 * Usage:
 *   SUPABASE_URL=https://vqawanftlolsplxuwipw.supabase.co \
 *   SUPABASE_SERVICE_ROLE_KEY=sb_secret_xxx \
 *   node admin_Inspector.js list-users
 *
 * Or:
 *   SUPABASE_URL=https://vqawanftlolsplxuwipw.supabase.co \
 *   SUPABASE_SERVICE_ROLE_KEY=sb_secret_xxx \
 *   node admin_Inspector.js auth-settings
 *
 * NOTE: Keep your service role key secret. Do not commit it to source control.
 */

import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY) {
  console.error('Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY environment variables.');
  process.exit(1);
}

// Create a Supabase client using the service role key (bypasses RLS).
const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, {
  auth: { persistSession: false },
  global: { headers: { 'x-client-info': 'admin_inspector/1.0' } },
});

async function listUsers(page = 1, perPage = 100) {
  // Uses the admin.listUsers helper from supabase-js
  try {
    const res = await supabase.auth.admin.listUsers({ page, perPage });
    if (res.error) throw res.error;
    const users = res.data.users || [];
    console.log(`Got ${users.length} users (page ${page})`);
    // Print limited user info to avoid exposing sensitive fields
    users.forEach((u) => {
      console.log({
        id: u.id,
        email: u.email,
        confirmed_at: u.confirmed_at,
        phone: u.phone,
        created_at: u.created_at,
        last_sign_in_at: u.last_sign_in_at || null,
        user_metadata: u.user_metadata || null,
      });
    });
  } catch (err) {
    console.error('Error listing users:', err.message || err);
    process.exitCode = 2;
  }
}

async function fetchAuthSettings() {
  // There is no direct supabase-js admin method for auth settings,
  // so call the Admin REST endpoint using fetch with the service_role key.
  try {
    const adminUrl = `${SUPABASE_URL.replace(/\/$/, '')}/auth/v1/admin/settings`;
    const res = await fetch(adminUrl, {
      method: 'GET',
      headers: {
        apikey: SUPABASE_SERVICE_ROLE_KEY,
        Authorization: `Bearer ${SUPABASE_SERVICE_ROLE_KEY}`,
        'Content-Type': 'application/json',
      },
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`${res.status} ${text}`);
    }
    const settings = await res.json();
    // Summarize settings to avoid large dump
    const summary = {
      site_url: settings.site_url,
      external_email_enabled: settings.external_email_enabled,
      external_oauth_providers: settings.external_oauth_providers || [],
      smtp_configured: !!settings.smtp,
      // confirmation/magic link settings might be nested; show common flags
      email: settings.email || null,
    };
    console.log('Auth settings summary:', summary);
  } catch (err) {
    console.error('Error fetching auth settings:', err.message || err);
    process.exitCode = 3;
  }
}

async function main() {
  const args = process.argv.slice(2);
  const cmd = args[0] || 'help';

  if (cmd === 'help') {
    console.log('Usage: node admin_Inspector.js <command>');
    console.log('Commands:');
    console.log('  list-users [page] [perPage]   List users (admin).');
    console.log('  auth-settings                 Fetch auth settings summary.');
    console.log('  help                          Show this help.');
    process.exit(0);
  }

  if (cmd === 'list-users') {
    const page = parseInt(args[1], 10) || 1;
    const perPage = parseInt(args[2], 10) || 100;
    await listUsers(page, perPage);
    return;
  }

  if (cmd === 'auth-settings') {
    await fetchAuthSettings();
    return;
  }

  console.log(`Unknown command: ${cmd}`);
  process.exit(1);
}

main().catch((err) => {
  console.error('Fatal error:', err);
  process.exit(99);
});
