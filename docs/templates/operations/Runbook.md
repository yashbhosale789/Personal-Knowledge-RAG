# Operations Runbook

Use this as the index for verified incident procedures.

## Common symptoms
- Application unavailable.
- HTTPS/certificate issue.
- High latency or memory pressure.
- LLM provider rate limit or outage.
- Empty/poor retrieval results.
- Vector-store/index failure.
- Unexpected token/provider cost.
- Deployment failure.
- Suspected credential exposure.

## Diagnostic sequence
1. Check current deployment/revision and recent changes.
2. Check health endpoint and service logs.
3. Check host CPU, memory, disk, and process state.
4. Check provider errors and rate limits.
5. Check retrieval/index health.
6. Check metrics and traces with sensitive content handled safely.
7. Apply the relevant runbook or rollback procedure.

Add exact commands only after verifying them on the actual host and operating system.
