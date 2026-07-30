CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    file_name VARCHAR(255) NOT NULL,
    file_type VARCHAR(20) NOT NULL,

    source_container VARCHAR(100) NOT NULL,
    source_blob_name TEXT NOT NULL,

    mime_type VARCHAR(100),
    file_size_bytes BIGINT,
    checksum VARCHAR(64),

    processing_status VARCHAR(30) NOT NULL DEFAULT 'pending',
    processing_error TEXT,

    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT documents_source_blob_unique
        UNIQUE (source_container, source_blob_name),

    CONSTRAINT documents_file_type_check
        CHECK (file_type IN ('pdf', 'docx')),

    CONSTRAINT documents_processing_status_check
        CHECK (
            processing_status IN (
                'pending',
                'processing',
                'completed',
                'failed'
            )
        ),

    CONSTRAINT documents_file_size_check
        CHECK (
            file_size_bytes IS NULL
            OR file_size_bytes >= 0
        )
);