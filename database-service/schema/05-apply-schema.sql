\set ON_ERROR_STOP on

\echo 'Applying documents schema...'
\ir 01-documents.sql

\echo 'Applying document chunks schema...'
\ir 02-document-chunks.sql

\echo 'Applying document images schema...'
\ir 03-document-images.sql

\echo 'Applying indexes...'
\ir 04-indexes.sql

\echo 'Database schema applied successfully.'