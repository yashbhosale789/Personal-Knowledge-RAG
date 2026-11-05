# Operations

How the production system is hosted, deployed, monitored and recovered. Architecture context: [ARCHITECTURE.md](ARCHITECTURE.md#delivery-and-operations).

**Contents:** [Production host](#production-host) · [Continuous delivery](#continuous-delivery) · [Monitoring, SLOs and alerts](#monitoring-slos-and-alerts) · [Data, backup and recovery](#data-backup-and-recovery) · [Secrets](#secrets) · [Logging and retention](#logging-and-retention) · [Cost](#cost) · [Runbooks](#runbooks)

---

## Production host

One AWS EC2 `t3.small` (2 GiB) running Docker Compose (`rag-project/docker-compose.prod.yml`). Every container has a memory cap; the caps sum past the host on purpose, so a runaway container is OOM-killed and restarted instead of starving the rest.

| Service | Image | Memory cap | Exposed |
| --- | --- | --- | --- |
| Caddy | `caddy:2` | 128 MiB | 80, 443 (TLS for the DuckDNS domain) |
| App | `ghcr.io/yashbhosale789/personal-knowledge-rag:<sha>` | 1 GiB | through Caddy only |
| Redis Stack | `redis/redis-stack` (pinned digest) | 192 MiB, plus `maxmemory` | internal |
| Prometheus | `prom/prometheus:v3.15.0` | 256 MiB | internal; 30-day retention |
| Grafana | `grafana/grafana:13.2.2` | 256 MiB | `127.0.0.1:3000` on the host (reach it through an SSM port-forwarding session) |

Caddy returns 404 for `/metrics*` and `/ingest*`, and caps `/documents` bodies at 11 MiB before FastAPI spools them to disk.

## Continuous delivery

1. A merge to `main` that touches `rag-project/**` (or the workflow) runs **Build and Push Image** (`.github/workflows/build-push.yml`).
2. It builds the image, React UI included, and pushes it to GHCR tagged with the commit SHA.
3. It runs `rag-project/deploy.sh` on the instance through **AWS Systems Manager** Run Command, so no SSH port is open.
4. `deploy.sh` pulls the image and copies its own config out of it (itself, the compose file, Caddyfile, Prometheus and Grafana config), restarting only the services whose config changed, so the server always matches the deployed commit. It then recreates only the app container and waits for it to be healthy.
5. On success it clears the semantic cache, sends a warm-up query, and the workflow runs a smoke test.
6. If the new version is unhealthy, it redeploys the previous image automatically. Rollback has been drilled on production.

Always deploy through `deploy.sh` (it sets `IMAGE_TAG` and `COMPOSE_PROFILES`), never a bare `docker compose up -d`.

## Monitoring, SLOs and alerts

**Provisional SLOs** for `POST /query` over a rolling 28-day window, computed by the recording rules in `rag-project/prometheus-rules.yml`:

| SLO | Target | Error budget |
| --- | --- | --- |
| Availability: response is not 5xx | 99% | 1% of requests |
| Latency: completes within 10 s | 95% | 5% of requests |

The 10 s target comes from measured latency (about 3–4 s per answered query). They stay provisional because single-user traffic is too sparse to tune against; a load test is Phase 15.4.

**Alerts** (Grafana, `rag-project/grafana/provisioning/alerting/`, emailed to `ALERT_EMAIL`). All were fire-tested:

| Alert | Fires when | Severity |
| --- | --- | --- |
| Availability fast burn | 5xx ratio > 14.4% over 1 h and 5 m, for 2 m | page |
| Availability slow burn | 5xx ratio > 6% over 6 h and 30 m, for 15 m | ticket |
| Latency fast burn | share over 10 s > 72% over 1 h and 5 m, for 2 m | page |
| Latency slow burn | share over 10 s > 30% over 6 h and 30 m, for 15 m | ticket |
| App down | Prometheus cannot scrape the app for 2 m | page |
| LLM provider failures | one provider has ≥ 3 failed attempts in 30 m | ticket |
| LLM fallback rate | exhausted + rate-limited requests > 25% of successful ones over 1 h | ticket |

**From outside:** Prometheus cannot report its own host being down, so the **Uptime** workflow checks `/health` through Caddy every 10 minutes and GitHub emails on failure.

**Dashboard:** *RAG Pipeline Overview* (`rag-project/grafana/rag-pipeline-overview.json`): SLO compliance and error budget remaining, request rate, p95 latency, app up, provider errors, retries and latency, per-stage latency, tokens per minute by stage, query outcomes, cache-hit ratio, abstain and low-confidence rates, and the live prompt version.

**Tracing:** Langfuse Cloud, one trace per `/query` with the same request ID as the logs and metrics. Content is masked unless `TRACING_CAPTURE_CONTENT=true`.

Details: [Observability](docs/templates/engineering/Observability.md).

## Data, backup and recovery

| Volume | Holds | Backup |
| --- | --- | --- |
| `rag_chroma_data` + `rag_documents_data` | the index and its PDFs: **one unit**, back up and restore together | needed for uploads; the committed corpus can be rebuilt |
| `rag_feedback_data` | feedback (SQLite) | needed |
| Redis | cache and rate-limit counters | none: losing it costs cache hits only |

- An empty index volume is seeded from the image's built-in index on first mount; after that the volume wins, and a PDF merged to git reaches production only by uploading it or by a re-seed.
- Back up before a chromadb upgrade: a newer version may migrate the on-disk format.

Commands, re-seed and restore procedures: [Backup and recovery](docs/templates/operations/Backup_Recovery.md) and [Rollback](docs/templates/operations/Rollback.md).

## Secrets

- Production secrets live in the server's `.env` (template: `rag-project/.env.sample`), never in git or the image.
- GitHub OIDC is blocked by the account's managed policy, so deploys use a least-privilege AWS key rotated every 90 days.
- One incident (keys committed, 2026-10-29) is written up in the [roadmap](docs/architecture/roadmap.md) with its fixes. See [Secrets management](docs/templates/security/Secrets_Management.md).

## Logging and retention

- JSON logs with the request ID on every line; Docker log rotation (3 × 10 MB per service).
- Feedback text (query, answer, comment) is deleted after 90 days; Prometheus keeps 30 days.
- Policy: [Data privacy](docs/templates/security/Data_Privacy.md).

## Cost

$0: one EC2 instance, free-tier LLM providers and Langfuse Cloud's free tier. Before any infrastructure change, confirm the AWS plan and the instance's CPU-credit mode (T3 defaults to *unlimited*, which can bill surplus CPU). "Cost" in metrics means free-tier quota, tracked as tokens and calls per provider per day. See [Cost management](docs/templates/operations/Cost_Management.md).

## Runbooks

- [Operations runbook](docs/templates/operations/Runbook.md): common symptoms and a diagnostic sequence
- [Redis Stack guide](docs/runbooks/redis-stack-guide.md): cache inspection, RediSearch index commands
- [Deployment](docs/templates/operations/Deployment.md) · [CI/CD](docs/templates/operations/CI_CD.md) · [Incident response](docs/templates/security/Incident_Response.md)
