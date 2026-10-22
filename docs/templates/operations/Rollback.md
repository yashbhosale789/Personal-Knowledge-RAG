# Rollback

## Preconditions
Identify the last known-good release/commit and the actual deployment mechanism before executing rollback.

## Procedure to complete from verified infrastructure
1. Stop or limit further deployments if a pipeline issue is suspected.
2. Select the known-good revision.
3. Deploy it using the approved workflow.
4. Verify health, HTTPS, and a safe smoke test.
5. Inspect logs, errors, and resource use.
6. Record the rollback reason and follow-up actions.

## Data/index caution
Application rollback may not roll back vector-store data, uploaded documents, schemas, or external provider state. Document those separately and avoid destructive restoration without a verified backup.

## Verification
Record the deployed revision, test results, and any remaining degradation. Do not claim rollback succeeded without verification.
