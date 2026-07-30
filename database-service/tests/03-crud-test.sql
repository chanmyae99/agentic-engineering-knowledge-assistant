\set ON_ERROR_STOP on

\echo 'Starting database CRUD test...'

BEGIN;

DO $$
DECLARE
    test_document_id UUID;
    chunk_count INTEGER;
    image_count INTEGER;
BEGIN
    INSERT INTO documents (
        file_name,
        file_type,
        source_container,
        source_blob_name,
        mime_type,
        file_size_bytes,
        checksum,
        processing_status,
        metadata
    )
    VALUES (
        'sprint-3-test.pdf',
        'pdf',
        'test-container',
        'tests/sprint-3-test.pdf',
        'application/pdf',
        1024,
        'sprint-3-test-checksum',
        'processing',
        '{"test": true}'::jsonb
    )
    RETURNING id INTO test_document_id;

    INSERT INTO document_chunks (
        document_id,
        chunk_index,
        content,
        embedding,
        content_type,
        token_count,
        section_path,
        metadata
    )
    VALUES (
        test_document_id,
        0,
        'Workers must wear appropriate personal protective equipment.',
        array_fill(0.01::real, ARRAY[1536])::vector,
        'text',
        8,
        '["Safety", "PPE"]'::jsonb,
        '{"page_number": 1}'::jsonb
    );

    INSERT INTO document_images (
        document_id,
        image_index,
        page_number,
        image_file_name,
        image_container,
        image_blob_name,
        caption,
        caption_embedding,
        mime_type,
        width,
        height,
        metadata
    )
    VALUES (
        test_document_id,
        0,
        1,
        'sprint-3-test-image.png',
        'test-images',
        'tests/sprint-3-test-image.png',
        'Diagram showing required protective equipment.',
        array_fill(0.02::real, ARRAY[1536])::vector,
        'image/png',
        800,
        600,
        '{"test": true}'::jsonb
    );

    SELECT COUNT(*)
    INTO chunk_count
    FROM document_chunks
    WHERE document_id = test_document_id;

    IF chunk_count <> 1 THEN
        RAISE EXCEPTION
            'Expected one test chunk, found %',
            chunk_count;
    END IF;

    SELECT COUNT(*)
    INTO image_count
    FROM document_images
    WHERE document_id = test_document_id;

    IF image_count <> 1 THEN
        RAISE EXCEPTION
            'Expected one test image, found %',
            image_count;
    END IF;

    DELETE FROM documents
    WHERE id = test_document_id;

    SELECT COUNT(*)
    INTO chunk_count
    FROM document_chunks
    WHERE document_id = test_document_id;

    SELECT COUNT(*)
    INTO image_count
    FROM document_images
    WHERE document_id = test_document_id;

    IF chunk_count <> 0 OR image_count <> 0 THEN
        RAISE EXCEPTION
            'Cascade deletion failed';
    END IF;
END
$$;

ROLLBACK;

\echo 'CRUD and cascade test passed.'