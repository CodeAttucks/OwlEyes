-- ============================================================
-- Row Level Security Policies
-- Applies to: organizations, users, projects, fiber_routes,
--             service_locations, expenditures
--
-- auth.uid() = the Supabase-authenticated user's UUID.
-- All tables default-deny; policies grant access explicitly.
-- The anon (publishable) key only reaches rows allowed below.
-- The service role bypasses RLS entirely.
-- ============================================================

-- ------------------------------------------------------------
-- organizations
-- ------------------------------------------------------------
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;

-- Users may only see the organization they belong to.
CREATE POLICY org_read ON organizations
  FOR SELECT
  USING (id IN (SELECT org_id FROM users WHERE id = auth.uid()));

-- Only service role may insert/update/delete organizations.

-- ------------------------------------------------------------
-- users
-- ------------------------------------------------------------
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- A user may read their own record.
CREATE POLICY user_read_self ON users
  FOR SELECT
  USING (id = auth.uid());

-- Users in the same org may see each other (e.g. team members list).
CREATE POLICY user_read_org ON users
  FOR SELECT
  USING (org_id IN (SELECT org_id FROM users WHERE id = auth.uid()));

-- A user may update only their own record.
CREATE POLICY user_update_self ON users
  FOR UPDATE
  USING (id = auth.uid());

-- ------------------------------------------------------------
-- projects
-- ------------------------------------------------------------
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;

-- Users may read/write projects that belong to their organization.
CREATE POLICY org_access ON projects
  FOR ALL
  USING (org_id IN (SELECT org_id FROM users WHERE id = auth.uid()));

-- ------------------------------------------------------------
-- fiber_routes
-- ------------------------------------------------------------
ALTER TABLE fiber_routes ENABLE ROW LEVEL SECURITY;

-- Users may read/write fiber routes for projects in their org.
CREATE POLICY fiber_org_access ON fiber_routes
  FOR ALL
  USING (
    project_id IN (
      SELECT p.id FROM projects p
      JOIN users u ON u.org_id = p.org_id
      WHERE u.id = auth.uid()
    )
  );

-- ------------------------------------------------------------
-- service_locations
-- ------------------------------------------------------------
ALTER TABLE service_locations ENABLE ROW LEVEL SECURITY;

-- Service locations are public geospatial coverage data — allow
-- anonymous read (safe for the publishable/anon key).
CREATE POLICY service_locations_public_read ON service_locations
  FOR SELECT
  USING (true);

-- Only authenticated users (service role or backend) may mutate.
CREATE POLICY service_locations_auth_write ON service_locations
  FOR ALL
  USING (auth.role() = 'authenticated');

-- ------------------------------------------------------------
-- expenditures
-- ------------------------------------------------------------
ALTER TABLE expenditures ENABLE ROW LEVEL SECURITY;

-- Users may only see expenditures tied to their org's projects.
CREATE POLICY expenditures_org_access ON expenditures
  FOR ALL
  USING (
    project_id IN (
      SELECT p.id FROM projects p
      JOIN users u ON u.org_id = p.org_id
      WHERE u.id = auth.uid()
    )
  );