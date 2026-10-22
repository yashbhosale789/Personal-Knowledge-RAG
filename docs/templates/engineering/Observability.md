# Observability

## Goals
Diagnose failures, understand latency, track resource use, and connect individual requests to relevant pipeline stages without leaking sensitive data.

## Signal categories
- Metrics: request volume, error rate, latency, resource utilization, provider failures, token use, estimated cost.
- Logs: structured events, errors, and operational state.
- Traces: per-request flow across retrieval, reranking, embedding, and generation where supported.
- RAG evaluation: retrieval relevance, groundedness, answer quality, and regression results.

## Existing tooling to verify
Prometheus and Grafana were previously reported for metrics and dashboards. A tracing tool such as Langfuse was considered but should not be treated as configured until verified.

## Safe telemetry
- Never record credentials.
- Avoid storing full document contents or prompts by default when they may contain sensitive data.
- Apply redaction, access control, and retention limits.
- Add request/run identifiers for correlation where appropriate.
- Document sampling and failure behavior.

## Alerts and dashboards
Define alerts from measured service requirements. Do not invent thresholds without a baseline and operational rationale.
