# Backup and Recovery

## Inventory
Identify whether each item is persistent and whether it requires backup:
- Original uploaded documents.
- Extracted/chunked content.
- Vector-store/index data.
- Configuration that is safe to back up.
- Evaluation datasets and results.
- Application state.
- Logs/traces where retention is required.

Never back up secrets into an unapproved location.

## Current state (verified 2026-10-29)
- **Source documents:** `rag-project/data/documents/*.pdf`, committed to git (the repo is public, so the corpus is public). Git is the backup.
- **Index:** Chroma (`rag-project/storage/chroma/`) and the BM25 chunk file (`rag-project/storage/chunks.json`) are derived. `RUN python scripts/ingest.py` in the Dockerfile rebuilds both into every image, so there is nothing to back up.
- **Consequence (F-02, Phase 15.0):** documents added or deleted through `/ingest` live only in the running container and are lost on the next deploy or rollback.
- **Redis:** cache and rate-limit counters only, no volume; losing it costs cache hits, not data.

## Rebuilding the index from the source documents
This procedure is revised in Phase 15.0, when the index moves to a named volume and is built offline.

**Production** (the normal path: the image build is the rebuild):
1. Add, replace or remove PDFs under `rag-project/data/documents/` on a branch, and merge the PR. `build-push.yml` builds an image with a fresh index and deploys it.
   To restore the committed corpus without a change (for example, to discard `/ingest` edits), re-run the latest deploy job: `gh run rerun <run-id> --job <deploy-job-id>`.
2. `deploy.sh` flushes the semantic cache (`cache:*`) after a successful deploy. This matters because the cache namespace does not include the corpus and Redis survives app deploys. If that step logs "cache flush failed", clear it by hand:
   `sudo docker exec $(sudo docker ps -qf name=app) python -c "from src.llm.semantic_cache import clear_cache; print(clear_cache())"`
3. Smoke test: `/health` returns `pipeline_ready: true`, and one `/query` cites the expected source.

**Local** (dev or evaluation), from `rag-project/` with the venv active:
1. Delete `storage/`: chunk IDs are deterministic, so re-ingesting is idempotent, but chunks of a removed PDF stay in Chroma unless the directory is wiped.
2. `python scripts/ingest.py`, then check the printed document and chunk counts.
3. `python -m eval.tools.validate_dataset` must exit 0 (evidence spans still match `storage/chunks.json`). A changed corpus gets a new corpus identifier in eval records, so do not compare its runs with `c1` runs.

## Recovery objectives
Define acceptable recovery point (data loss) and recovery time based on actual needs; do not invent targets.

## Procedure
1. Identify the failure and select a known-good backup.
2. Verify backup integrity and provenance.
3. Restore to a safe location or controlled environment first when possible.
4. Rebuild derived indexes if necessary and supported.
5. Run integrity checks and retrieval smoke tests.
6. Switch traffic only after verification.
7. Record outcome and any data loss.

## Open items
Document actual backup frequency, storage location, retention, encryption, and last successful restore test.
