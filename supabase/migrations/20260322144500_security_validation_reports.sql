create table if not exists public.security_validation_reports (
  id bigint generated always as identity primary key,
  created_at timestamptz not null default now(),
  repository text not null,
  pull_request_number integer,
  sha text,
  run_id text,
  run_url text,
  report text not null,
  source_ip text,
  user_agent text
);

comment on table public.security_validation_reports is
  'Stores staging security validation reports submitted by CI.';

create index if not exists security_validation_reports_created_at_idx
  on public.security_validation_reports (created_at desc);

alter table public.security_validation_reports enable row level security;

-- No public policies are created. Service role can write/read for operational use.
