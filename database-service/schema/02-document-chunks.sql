CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    document_id UUID NOT NULL,

    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,

    embedding VECTOR(1536) NOT NULL,

    content_type VARCHAR(30) NOT NULL DEFAULT 'text',
    token_count INTEGER,

    section_path JSONB NOT NULL DEFAULT '[]'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,

    search_vector TSVECTOR
        GENERATED ALWAYS AS (
            to_tsvector(
                'english',
                COALESCE(content, '')
            )
        ) STORED,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT document_chunks_document_fk
        FOREIGN KEY (document_id)
        REFERENCES documents(id)
        ON DELETE CASCADE,

    CONSTRAINT document_chunks_document_index_unique
        UNIQUE (document_id, chunk_index),

    CONSTRAINT document_chunks_index_check
        CHECK (chunk_index >= 0),

    CONSTRAINT document_chunks_token_count_check
        CHECK (
            token_count IS NULL
            OR token_count >= 0
        ),

    CONSTRAINT document_chunks_content_not_blank
        CHECK (length(trim(content)) > 0),

    CONSTRAINT document_chunks_section_path_array
        CHECK (jsonb_typeof(section_path) = 'array'),

    CONSTRAINT document_chunks_metadata_object
        CHECK (jsonb_typeof(metadata) = 'object')
);