# Database Service

This service uses PostgreSQL with pgvector.

## Responsibilities

- Store source document metadata
- Store document chunks
- Store PDF page metadata
- Store DOCX heading metadata
- Store extracted-image metadata
- Store text and image-caption embeddings
- Support keyword and vector retrieval

## Storage Architecture

Azure Blob Storage stores:
- Original PDF and DOCX files
- Extracted images

PostgreSQL with pgvector stores:
- Document records
- Chunk content and metadata
- Image captions and metadata
- Embeddings

Binary files are not stored in PostgreSQL.