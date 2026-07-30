-- ============================================================
-- Documents indexes
-- ============================================================

CREATE INDEX IF NOT EXISTS documents_checksum_idx
    ON documents (checksum);

CREATE INDEX IF NOT EXISTS documents_processing_status_idx
    ON documents (processing_status);

CREATE INDEX IF NOT EXISTS documents_created_at_idx
    ON documents (created_at);


-- ============================================================
-- Document chunk indexes
-- ============================================================

CREATE INDEX IF NOT EXISTS document_chunks_document_id_idx
    ON document_chunks (document_id);

CREATE INDEX IF NOT EXISTS document_chunks_search_vector_idx
    ON document_chunks
    USING GIN (search_vector);

CREATE INDEX IF NOT EXISTS document_chunks_metadata_idx
    ON document_chunks
    USING GIN (metadata);

CREATE INDEX IF NOT EXISTS document_chunks_section_path_idx
    ON document_chunks
    USING GIN (section_path);

CREATE INDEX IF NOT EXISTS document_chunks_embedding_hnsw_idx
    ON document_chunks
    USING hnsw (embedding vector_cosine_ops);


-- ============================================================
-- Document image indexes
-- ============================================================

CREATE INDEX IF NOT EXISTS document_images_document_id_idx
    ON document_images (document_id);

CREATE INDEX IF NOT EXISTS document_images_metadata_idx
    ON document_images
    USING GIN (metadata);

CREATE INDEX IF NOT EXISTS document_images_caption_embedding_hnsw_idx
    ON document_images
    USING hnsw (caption_embedding vector_cosine_ops)
    WHERE caption_embedding IS NOT NULL;