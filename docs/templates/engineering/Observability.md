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

## SLOs (provisional, Phase 13.5; finalised in Phase 15.4)
Both cover `POST /query` only, over a rolling **28-day window**. They are computed from `http_requests_total` and `http_request_duration_seconds` by the recording rules in `rag-project/prometheus-rules.yml`; Prometheus keeps 30 days so the window fits.

| SLO | Target | Error budget (28 d) | Recorded ratio |
| --- | --- | --- | --- |
| Availability: response is not 5xx | 99% | 1% of requests | `slo:query_errors:ratio_rate{5m,30m,1h,6h,28d}` |
| Latency: completes within 10 s (p95 < 10 s) | 95% | 5% of requests | `slo:query_slow:ratio_rate{5m,30m,1h,6h,28d}` |

Budget remaining = `1 - ratio_rate28d / budget` (0.01 or 0.05), shown on the top row of the RAG dashboard. The 10 s target is set from measured latency: about 3-4 s per answered query after 2026-10-29, when the citation verifier moved to Groq qwen (it was 18-24 s per call on the Gemini free tier). The `le="10.0"` bucket the latency rules read is pinned by a test; buckets reach 30 s so Phase 15.4 can measure the true p95. Traffic is a single user, so one failed request is a large share of a quiet hour; the thresholds are provisional for that reason.

## Alerts and dashboards
Define alerts from measured service requirements. Do not invent thresholds without a baseline and operational rationale.

Grafana alerting (`rag-project/grafana/provisioning/alerting/`) emails the `ALERT_EMAIL` contact point. Provisional thresholds:

| Alert | Fires when | Severity |
| --- | --- | --- |
| Availability fast burn | 5xx ratio > 14.4% over both 1 h and 5 m (14.4x burn: 2% of the 28-day budget per hour), for 2 m | page |
| Availability slow burn | 5xx ratio > 6% over both 6 h and 30 m (6x burn), for 15 m | ticket |
| Latency fast burn | Share over 10 s > 72% over both 1 h and 5 m (14.4x of the 5% budget), for 2 m | page |
| Latency slow burn | Share over 10 s > 30% over both 6 h and 30 m (6x), for 15 m | ticket |
| App down | Prometheus cannot scrape `rag-app` for 2 m | page |
| LLM provider failures | One provider has 3 or more failed call attempts in 30 m | ticket |
| LLM fallback rate | Exhausted plus rate-limited provider requests exceed 25% of successful ones over 1 h | ticket |

The host being down is outside Prometheus's view: the `Uptime` GitHub Actions workflow checks `/health` every 10 minutes from outside, and GitHub emails on failure.
