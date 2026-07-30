CREATE TABLE IF NOT EXISTS document_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    document_id UUID NOT NULL,
    image_index INTEGER NOT NULL,

    page_number INTEGER,

    image_file_name VARCHAR(255),
    image_container VARCHAR(100),
    image_blob_name TEXT,

    caption TEXT,
    caption_embedding VECTOR(1536),

    mime_type VARCHAR(100),
    width INTEGER,
    height INTEGER,

    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT document_images_document_fk
        FOREIGN KEY (document_id)
        REFERENCES documents(id)
        ON DELETE CASCADE,

    CONSTRAINT document_images_document_index_unique
        UNIQUE (document_id, image_index),

    CONSTRAINT document_images_index_check
        CHECK (image_index >= 0),

    CONSTRAINT document_images_page_number_check
        CHECK (
            page_number IS NULL
            OR page_number > 0
        ),

    CONSTRAINT document_images_width_check
        CHECK (
            width IS NULL
            OR width > 0
        ),

    CONSTRAINT document_images_height_check
        CHECK (
            height IS NULL
            OR height > 0
        ),

    CONSTRAINT document_images_metadata_object
        CHECK (jsonb_typeof(metadata) = 'object')
);