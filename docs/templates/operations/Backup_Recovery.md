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
