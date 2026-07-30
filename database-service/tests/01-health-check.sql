\set ON_ERROR_STOP on

\echo 'Checking PostgreSQL database...'

SELECT
    current_database() AS database_name,
    current_user AS database_user,
    version() AS postgres_version;

\echo 'Checking required extensions...'

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_extension
        WHERE extname = 'vector'
    ) THEN
        RAISE EXCEPTION 'Required extension vector is not installed';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_extension
        WHERE extname = 'pgcrypto'
    ) THEN
        RAISE EXCEPTION 'Required extension pgcrypto is not installed';
    END IF;
END
$$;

SELECT
    extname,
    extversion
FROM pg_extension
WHERE extname IN ('vector', 'pgcrypto')
ORDER BY extname;

\echo 'Database health check passed.'