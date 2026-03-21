INSERT INTO organizations (id, name, type)
VALUES (gen_random_uuid(), 'WA State Broadband Office', 'State');

INSERT INTO projects (id, name, state, status)
VALUES
(gen_random_uuid(), 'WA BEAD Phase 1', 'WA', 'active'),
(gen_random_uuid(), 'Tribal Fiber Expansion', 'WA', 'planning');

-- Generate fiber + locations
INSERT INTO fiber_routes (project_id, geom, miles)
SELECT id, ST_MakeLine(ST_Point(-120.3,47.4), ST_Point(-120.6,47.7)), 25
FROM projects LIMIT 1;

INSERT INTO service_locations (geom, served)
SELECT ST_Point(-120.4 + random()/10, 47.5 + random()/10), (random() > 0.5)
FROM generate_series(1,500);