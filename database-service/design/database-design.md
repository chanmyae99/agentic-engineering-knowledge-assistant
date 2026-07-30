# Database Design

## Agentic Engineering Knowledge Assistant

## 1. Storage Architecture

The system uses two storage technologies:

### Azure Blob Storage

Azure Blob Storage stores:

- Original PDF documents
- Original DOCX documents
- Extracted images from PDF documents

Large binary files are not stored inside PostgreSQL.

### PostgreSQL with pgvector

PostgreSQL stores:

- Source-document metadata
- Text chunks
- PDF page metadata
- DOCX heading and section metadata
- Extracted-image metadata
- Image captions
- Text embeddings
- Image-caption embeddings

The pgvector extension supports semantic similarity search.

## 2. Ingestion Flow

```text
Azure Blob Storage
        |
        v
Backend downloads document
        |
        v
Extract text and structure
        |
        +----------------------+
        |                      |
        v                      v
Create text chunks       Extract PDF images
        |                      |
        v                      v
Generate embeddings      Generate image captions
        |                      |
        |                Generate caption embeddings
        |                      |
        v                      v
Store in PostgreSQL      Upload images to Azure Blob
                               |
                               v
                        Store image metadata
                        and vectors in PostgreSQL