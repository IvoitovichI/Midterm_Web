-- psql entry point for importing into an empty PostgreSQL database.
\set ON_ERROR_STOP on
BEGIN;
SELECT pg_advisory_xact_lock(73103101);
\ir schema.sql
\ir seed.sql
COMMIT;
