FROM pgvector/pgvector:pg16

COPY init/01-extensions.sql /docker-entrypoint-initdb.d/01-extensions.sql
COPY init/02-apply-schema.sql /docker-entrypoint-initdb.d/02-apply-schema.sql

COPY schema/ /docker-entrypoint-initdb.d/schema/

EXPOSE 5432