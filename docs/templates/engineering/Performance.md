# Performance and Capacity

## Measure before optimizing
Capture baseline latency, error rates, memory/CPU use, retrieval time, provider time, and token use for representative workloads.

## Workload limits to define
- Maximum upload size and pages/characters.
- Maximum query/context size.
- Request timeout and provider timeout.
- Retry count and backoff.
- Concurrency and queue limits.
- Maximum retrieval candidates and reranking candidates.
- Cache policy and invalidation behavior.
- Expected request volume.

## Validation
Use repeatable tests and record hardware, corpus size, configuration, sample size, and observed results. Test overload and provider rate-limit behavior.

## Cost/quality trade-offs
Evaluate changes to chunk size, top-k, reranking, context length, and model selection against the evaluation baseline. Do not optimize tokens or latency at the expense of unmeasured quality regressions.
