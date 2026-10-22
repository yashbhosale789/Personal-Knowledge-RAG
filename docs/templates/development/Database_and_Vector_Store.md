# Database and Vector Store

## Current remembered context
Chroma has been used as the local vector store. Verify the current implementation, collection names, persistence configuration, metadata schema, and embedding model before executing operations.

## Document
- Store initialization and persistence.
- Collection naming and schema.
- Chunk identifiers and source metadata.
- Embedding model and vector dimensionality compatibility.
- Ingestion/upsert and duplicate handling.
- Query filters and access-control behavior.
- Index rebuild and migration procedure.
- Deletion semantics.
- Backup/recovery.
- Integrity checks and diagnostic commands.

## Safety
- Treat destructive collection deletion or rebuilding as a data-changing operation.
- Verify the target collection and backup/rebuild path before running destructive commands.
- Avoid relying on private/internal library attributes unless there is no supported alternative.
- Never expose sensitive document contents in diagnostic output.
