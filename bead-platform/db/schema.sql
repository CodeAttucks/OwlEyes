-- Includes organizations, users, projects, GIS, finance, construction, analytics
-- Full schema with 56 tables (basic implementation for key tables)

CREATE EXTENSION IF NOT EXISTS postgis;

-- Organizations
CREATE TABLE organizations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  type TEXT
);

-- Users
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID,
  email TEXT UNIQUE NOT NULL
);

-- Projects
CREATE TABLE projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID,
  name TEXT NOT NULL,
  state TEXT,
  status TEXT
);

-- Fiber Routes
CREATE TABLE fiber_routes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID,
  geom GEOMETRY(LINESTRING, 4326),
  miles FLOAT
);

-- Service Locations
CREATE TABLE service_locations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  geom GEOMETRY(POINT, 4326),
  served BOOLEAN
);

-- Expenditures
CREATE TABLE expenditures (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID,
  amount DECIMAL(10,2),
  description TEXT
);

-- Placeholder for remaining 50 tables (to be expanded)
-- Add additional tables as needed for full 56-table schema

-- Foreign Key Constraints
ALTER TABLE projects ADD CONSTRAINT fk_org FOREIGN KEY (org_id) REFERENCES organizations(id);
ALTER TABLE users ADD CONSTRAINT fk_user_org FOREIGN KEY (org_id) REFERENCES organizations(id);
ALTER TABLE fiber_routes ADD CONSTRAINT fk_project FOREIGN KEY (project_id) REFERENCES projects(id);
ALTER TABLE expenditures ADD CONSTRAINT fk_project_exp FOREIGN KEY (project_id) REFERENCES projects(id);

-- Indexes
CREATE INDEX idx_fiber_geom ON fiber_routes USING GIST (geom);
CREATE INDEX idx_locations_geom ON service_locations USING GIST (geom);