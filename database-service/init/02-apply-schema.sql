\set ON_ERROR_STOP on

\echo 'Applying application database schema...'

\ir /docker-entrypoint-initdb.d/schema/05-apply-schema.sql

\echo 'Application database initialization completed.'
