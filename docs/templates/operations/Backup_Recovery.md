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

## Current state (revised 2026-11-02, Phase 15.0 PR 2)
- **Committed corpus:** `rag-project/data/documents/*.pdf` in git (the repo is public, so the corpus is public). The image bakes it into an index at build time (`RUN python scripts/ingest.py`).
- **Production index and documents** live in two named volumes on the app container:

  | Volume | Mounted at | Holds |
  | --- | --- | --- |
  | `rag_chroma_data` | `/app/storage/chroma` | Chroma: chunks, embeddings, metadata |
  | `rag_documents_data` | `/app/data/documents` | the PDFs, including uploads |

  The two are **one unit**: each chunk's `source` is the absolute path of its PDF in the documents volume. Back them up and restore them together.
- **Uploads** (`POST /documents`, the UI) and deletes change only these volumes. An uploaded PDF exists nowhere else until you back it up or commit it to git.
- **BM25** is rebuilt in memory from Chroma; nothing to back up. `chunks.json` is an eval-only export inside the image, not in a volume; prod may diverge from it.
- **Feedback** (`rag_feedback_data`) is independent of the index. Nothing below touches it.
- **Redis:** cache and rate-limit counters only, no volume; losing it costs cache hits, not data.

## How the volumes behave
- **First mount:** Docker fills an empty named volume from the image, so the first deploy with volumes starts from the image's baked index (236 PDFs, 1,295 chunks since 2026-11-06). After that **the volume wins**: a later image's baked index is ignored. A PDF merged to git reaches prod only by uploading it, or by a re-seed (below).
- **Deploy:** `deploy.sh` recreates the app with the same volumes; uploads survive.
- **Rollback to an image from before Phase 15.0 PR 2:** `deploy.sh` copies the `docker-compose.prod.yml` shipped in the *target* image, and that file mounts no index volumes. The app serves that image's own baked index, and uploads are invisible but untouched (Compose never deletes named volumes). The next forward deploy mounts the volumes again and the uploads are back. That image never opens the volumes, so no Chroma version reads another's files.
- **Rollback between two images that both mount the volumes:** both read the same files. Safe while both run the same chromadb (1.5.9 at PR 2).
- **chromadb upgrades:** a newer chromadb may migrate the on-disk format the first time it opens the volume, and an older one may then fail to read it. Before deploying a chromadb bump, take a backup. If you roll back across the bump, restore that backup (uploads made after it are lost) or rebuild the index (re-seed B).

## Production commands
Run on the instance as `ubuntu` (no sudo), from `/home/ubuntu/rag`. Every block starts with:
```bash
cd ~/rag && export IMAGE_TAG="$(cat .image_tag)"
C="docker compose -f docker-compose.prod.yml"
IMG="ghcr.io/yashbhosale789/personal-knowledge-rag:$IMAGE_TAG"
```
Each block stops the app for a moment (the `Uptime` workflow may alert) and never runs a bare `up -d`.

**Back up both index volumes.** The app is stopped so Chroma's SQLite file is copied in a consistent state:
```bash
mkdir -p backups
$C stop app
docker run --rm --user root -v rag_chroma_data:/v/chroma:ro -v rag_documents_data:/v/documents:ro \
  -v "$PWD/backups:/b" "$IMG" tar czf "/b/index-$(date +%F-%H%M).tgz" -C /v chroma documents
$C start app
ls -lh backups/
```
Then copy the file off the instance (for example `scp` from your machine). A backup on the same disk does not survive losing the instance, and it uses space that `deploy.sh` needs (it aborts below 6 GB free), so keep only the latest few. Take one before a chromadb bump, before a re-seed, and after uploads you would not want to lose.

**Restore a backup** (replaces both volumes' contents):
```bash
$C stop app
docker run --rm --user root -v rag_chroma_data:/v/chroma -v rag_documents_data:/v/documents \
  -v "$PWD/backups:/b:ro" "$IMG" sh -c \
  'find /v/chroma /v/documents -mindepth 1 -delete && tar xzf /b/index-<stamp>.tgz -C /v && chown -R appuser:appuser /v'
$C start app
```

**Re-seed A: back to the image's corpus** (discards uploads; Compose seeds new volumes from the running image):
```bash
$C stop app && $C rm -f app
docker volume rm rag_chroma_data rag_documents_data
$C up -d app
```

**Re-seed B: rebuild the index from the documents volume** (keeps uploads; for example after a chromadb format problem, or after copying PDFs into the volume by hand). The script runs in a one-off container while the app is stopped. Do not `exec` it into the running app: two processes would write to the same embedded Chroma, and the app's BM25 reset is per process, so the app would keep serving its old keyword index anyway:
```bash
$C stop app
$C run --rm --no-deps app sh -c 'find /app/storage/chroma -mindepth 1 -delete && python scripts/ingest.py'
$C start app
```
The script exits 1 if any PDF is rejected; read its output before starting the app.

**After a restore or a re-seed**, flush the semantic cache, because its namespace does not include the corpus (`deploy.sh` does this after every deploy):
```bash
$C exec -T redis redis-cli EVAL "for _, k in ipairs(redis.call('KEYS', 'cache:*')) do redis.call('DEL', k) end return 1" 0
```
Smoke test: `/health` returns `pipeline_ready: true`, `GET /documents` lists the expected names with non-zero chunk counts, and one `/query` cites an expected source.

**Local** (dev or evaluation), from `rag-project/` with the venv active:
1. Delete `storage/`: chunk IDs are deterministic, so re-ingesting is idempotent, but chunks of a removed PDF stay in Chroma unless the directory is wiped.
2. `python scripts/ingest.py`, then check the printed document and chunk counts.
3. `python -m eval.tools.validate_dataset` must exit 0 (evidence spans still match `storage/chunks.json`). A changed corpus gets a new corpus identifier in eval records, so do not compare its runs with runs on another corpus id.

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
- No scheduled backup: single user, backups are taken by hand at the moments listed above.
- Off-instance storage location, retention and encryption are not set.
- Last restore test: local, Phase 15.0 PR 2 (2026-11-02). Not yet tested on production.
