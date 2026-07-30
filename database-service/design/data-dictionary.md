# Database Data Dictionary

## Table: documents

Purpose:

Stores one record for each original document in Azure Blob Storage.

| Column | Purpose |
|---|---|
| id | Unique document identifier |
| file_name | Original document filename |
| file_type | PDF or DOCX |
| source_container | Azure Blob container name |
| source_blob_name | Full Azure Blob path |
| mime_type | Document MIME type |
| file_size_bytes | Original document size |
| checksum | Used to detect duplicate documents |
| processing_status | Ingestion status |
| processing_error | Error details when ingestion fails |
| metadata | Additional document information |
| created_at | Record creation timestamp |
| updated_at | Last update timestamp |

## Table: document_chunks

Purpose:

Stores searchable text chunks and their embeddings.

| Column | Purpose |
|---|---|
| id | Unique chunk identifier |
| document_id | Parent document |
| chunk_index | Chunk sequence within the document |
| content | Searchable chunk text |
| chunk_type | Text, heading, table or other type |
| page_number | PDF page number |
| section | Section associated with the chunk |
| header_text | DOCX heading text |
| header_level | DOCX heading level |
| header_path | Full heading hierarchy |
| paragraph_number | DOCX paragraph number |
| token_count | Approximate number of tokens |
| embedding | Semantic embedding vector |
| metadata | Additional chunk information |
| created_at | Record creation timestamp |

## Table: document_images

Purpose:

Stores metadata and captions for images saved in Azure Blob Storage.

| Column | Purpose |
|---|---|
| id | Unique image identifier |
| document_id | Parent document |
| image_index | Image sequence within the document |
| page_number | PDF page where the image appears |
| image_file_name | Generated image filename |
| image_container | Azure Blob container |
| image_blob_name | Full image Blob path |
| mime_type | Image MIME type |
| width | Image width |
| height | Image height |
| file_size_bytes | Image file size |
| image_hash | Hash used for duplicate detection |
| caption | LLM-generated image description |
| caption_embedding | Semantic caption vector |
| metadata | Additional image information |
| created_at | Record creation timestamp |

## 5. Database Design Rules

### Document rules

- One database record represents one source document.
- The combination of `source_container` and `source_blob_name` must be unique.
- Original document bytes are stored only in Azure Blob Storage.
- Supported initial document types are PDF and DOCX.
- Processing status values are:
  - `pending`
  - `processing`
  - `completed`
  - `failed`

### Chunk rules

- Every chunk belongs to one document.
- A document can contain many chunks.
- `chunk_index` starts from zero and identifies the chunk order.
- PDF chunks may contain a page number.
- DOCX chunks may contain a heading, heading level and heading path.
- Every searchable chunk contains an embedding.
- Deleting a document must also delete its chunks.

### Image rules

- Every image belongs to one source document.
- Extracted image bytes are stored in Azure Blob Storage.
- PostgreSQL stores only the Blob location, image metadata, caption and caption embedding.
- Images are initially extracted only from PDFs.
- Deleting a document must also delete its image records.
- The backend is responsible for removing corresponding Azure Blob images.

### Embedding rules

- Text chunks and image captions use the same embedding model.
- The initial embedding model is `text-embedding-3-small`.
- The vector dimension is 1536.
- Changing to an embedding model with a different dimension requires a database migration and re-embedding.

### Retrieval rules

Hybrid retrieval combines:

1. PostgreSQL full-text keyword search
2. pgvector semantic similarity search

Text retrieval searches:

- `document_chunks.content`
- `document_chunks.embedding`

Image retrieval searches:

- `document_images.caption`
- `document_images.caption_embedding`