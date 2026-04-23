-- Migration: RLS policies for anon (publishable) key
-- Applies comprehensive row-level security to all application tables.
-- The anon key (sb_publishable_*) only reaches rows permitted below.
-- The service role bypasses RLS entirely.

-- ----------------------------------------------------------------
-- organizations
-- ----------------------------------------------------------------
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;

CREATE POLICY org_read ON organizations
  FOR SELECT
  USING (id IN (SELECT org_id FROM users WHERE id = auth.uid()));

-- ----------------------------------------------------------------
-- users
-- ----------------------------------------------------------------
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_read_self ON users
  FOR SELECT
  USING (id = auth.uid());

CREATE POLICY user_read_org ON users
  FOR SELECT
  USING (org_id IN (SELECT org_id FROM users WHERE id = auth.uid()));

CREATE POLICY user_update_self ON users
  FOR UPDATE
  USING (id = auth.uid());

-- ----------------------------------------------------------------
-- projects
-- ----------------------------------------------------------------
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;

-- Drop old policy (used auth.uid() directly against org_id — incorrect).
DROP POLICY IF EXISTS org_access ON projects;

CREATE POLICY org_access ON projects
  FOR ALL
  USING (org_id IN (SELECT org_id FROM users WHERE id = auth.uid()));

-- ----------------------------------------------------------------
-- fiber_routes
-- ----------------------------------------------------------------
ALTER TABLE fiber_routes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS fiber_org_access ON fiber_routes;

CREATE POLICY fiber_org_access ON fiber_routes
  FOR ALL
  USING (
    project_id IN (
      SELECT p.id FROM projects p
      JOIN users u ON u.org_id = p.org_id
      WHERE u.id = auth.uid()
    )
  );

-- ----------------------------------------------------------------
-- service_locations
-- ----------------------------------------------------------------
ALTER TABLE service_locations ENABLE ROW LEVEL SECURITY;

-- Public geospatial coverage data — safe for anon reads.
CREATE POLICY service_locations_public_read ON service_locations
  FOR SELECT
  USING (true);

CREATE POLICY service_locations_auth_write ON service_locations
  FOR ALL
  USING (auth.role() = 'authenticated');

-- ----------------------------------------------------------------
-- expenditures
-- ----------------------------------------------------------------
ALTER TABLE expenditures ENABLE ROW LEVEL SECURITY;

CREATE POLICY expenditures_org_access ON expenditures
  FOR ALL
  USING (
    project_id IN (
      SELECT p.id FROM projects p
      JOIN users u ON u.org_id = p.org_id
      WHERE u.id = auth.uid()
    )
  );
