ALTER TABLE projects ENABLE ROW LEVEL SECURITY;

CREATE POLICY org_access ON projects
USING (org_id = auth.uid());

ALTER TABLE fiber_routes ENABLE ROW LEVEL SECURITY;
CREATE POLICY fiber_org_access ON fiber_routes
USING (project_id IN (SELECT id FROM projects WHERE org_id = auth.uid()));