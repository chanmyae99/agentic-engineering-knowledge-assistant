# Database Integration Contract

## Database Technology

- PostgreSQL 16
- pgvector
- UTF-8 encoding
- Default schema: `public`

## Connection

### Docker Compose

The backend container must connect using the Docker Compose service name:

```env
DATABASE_URL=postgresql+psycopg://knowledge_admin:POSTGRES_PASSWORD@database:5432/knowledge_assistant