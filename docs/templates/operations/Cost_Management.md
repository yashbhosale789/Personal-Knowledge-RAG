# Cost Management

## Budget
Target budget: $0 unless the user explicitly approves spending. Verify current cloud account, provider free-tier terms, quotas, and expiration dates before relying on them.

## Cost sources to track
- Cloud compute, storage, networking, and logging.
- LLM input/output tokens.
- Embeddings.
- Reranking.
- Tracing/observability.
- Evaluation runs and retries.

## Controls
- Record token usage and estimated cost by pipeline stage.
- Bound request size, context length, retries, and concurrency.
- Cache only where correctness and invalidation are understood.
- Batch/resume evaluation when provider limits make that useful.
- Prefer offline paired comparisons when production traffic is too low for online A/B testing.
- Alert on quota exhaustion or unexpected usage where tooling supports it.

## Reporting
State assumptions, price source/date, provider, model, and uncertainty. Do not describe estimates as exact billing data.
