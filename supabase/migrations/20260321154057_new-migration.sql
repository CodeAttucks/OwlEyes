-- Migration: historical no-op
-- Intentionally empty migration retained to preserve migration ordering
-- across environments where this timestamp may already be recorded.
DO $$
BEGIN
	RAISE NOTICE 'Historical no-op migration retained for ordering compatibility.';
END $$;
