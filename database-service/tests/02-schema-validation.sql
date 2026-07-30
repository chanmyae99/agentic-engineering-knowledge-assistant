\set ON_ERROR_STOP on

\echo 'Validating required tables...'

DO $$
DECLARE
    missing_tables TEXT[];
BEGIN
    SELECT ARRAY_AGG(required_table)
    INTO missing_tables
    FROM (
        VALUES
            ('documents'),
            ('document_chunks'),
            ('document_images')
    ) AS required(required_table)
    WHERE to_regclass('public.' || required_table) IS NULL;

    IF missing_tables IS NOT NULL THEN
        RAISE EXCEPTION
            'Missing required tables: %',
            array_to_string(missing_tables, ', ');
    END IF;
END
$$;

\echo 'Validating vector columns...'

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'document_chunks'
          AND column_name = 'embedding'
          AND udt_name = 'vector'
    ) THEN
        RAISE EXCEPTION
            'document_chunks.embedding vector column is missing';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'document_images'
          AND column_name = 'caption_embedding'
          AND udt_name = 'vector'
    ) THEN
        RAISE EXCEPTION
            'document_images.caption_embedding vector column is missing';
    END IF;
END
$$;

\echo 'Validating important indexes...'

DO $$
DECLARE
    required_index TEXT;
BEGIN
    FOREACH required_index IN ARRAY ARRAY[
        'document_chunks_embedding_hnsw_idx',
        'document_chunks_search_vector_idx',
        'document_images_caption_embedding_hnsw_idx'
    ]
    LOOP
        IF NOT EXISTS (
            SELECT 1
            FROM pg_indexes
            WHERE schemaname = 'public'
              AND indexname = required_index
        ) THEN
            RAISE EXCEPTION
                'Required index % is missing',
                required_index;
        END IF;
    END LOOP;
END
$$;

\echo 'Schema validation passed.'