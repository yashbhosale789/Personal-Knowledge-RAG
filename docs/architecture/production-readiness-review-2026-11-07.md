# Production readiness review — 2026-11-07 (Phase 15.4)

Run of `prompts/workflows/production-readiness-review.md` against `main` at `f379ac7` plus the open 15.4 branches (torch 2.14.1, Trivy step). Code and config were read; no application code or infrastructure was changed during the review. Items that need load-test or image-scan evidence are marked **pending** and are filled in when that evidence exists.

## Verified issues

| # | Severity | Finding | Evidence | Impact | Remediation | Effort | Verify |
|---|---|---|---|---|---|---|---|
| R1 | Medium (**fixed** in 15.4: Caddy `request_body` 256 KB on `/query`, `/query/*`, `/feedback`; config validated with `caddy adapt`) | Unauthenticated requests can make the app buffer a body of any size on `/query`, `/query/stream` and `/feedback` | Caddy caps only `/documents` (`Caddyfile`, `request_body /documents { max_size 11MiB }`). FastAPI 0.141.1 reads and parses the whole body (`fastapi/routing.py` L433–446) before it resolves dependencies (L481), so `verify_api_key` runs after the body is in memory | A few large anonymous POSTs can push the 1 GiB app container towards its limit (OOM kill and restart = an outage on a single-instance service) | One `request_body` block in the Caddyfile for `/query*` and `/feedback`, e.g. `max_size 64KB` (largest valid `/query` body: 2,000-char query + 5 history turns ≈ 15 KB) | 3 lines, no app change | `curl` a 1 MB body to `/query` without a key: expect 413 from Caddy, not 401/422 from the app |
| R2 | Low (accepted: pin when Caddy next needs a change) | Caddy image is a floating tag | `docker-compose.prod.yml`: `image: caddy:2`; Redis is pinned by digest, Prometheus and Grafana by version | A manual `up` can pull a different Caddy than the one tested; it terminates TLS for the public endpoint | Pin a version tag (or digest) like the other services | 1 line | `docker compose config` shows the pinned image |

## Potential issues needing investigation

| # | Severity | Finding | Evidence | How to investigate |
|---|---|---|---|---|
| P1 | Medium | Concurrency ceiling inside the app | One uvicorn process; each `/query` pipeline runs in `asyncio.to_thread` (`api/core/retry.py`), whose default pool is `min(32, cpu + 4)` = 6 threads on 2 vCPU, held for the whole pipeline including LLM waits | k6 off-corpus phase at 10 concurrent users (**pending**) |
| P2 | Medium | Throughput is bounded by the Groq free tier, not the box | `gpt-oss-120b` 30 RPM / 8K TPM / 200K TPD (roadmap §13.3); an answered query is ~3 calls and ~2,400 tokens, so ~3 answered queries per minute; a 429 on sufficiency/generate re-runs the request on OpenRouter, then Gemini (`call_with_fallback`) | k6 answered phase (**pending**); record any fallback |
| P3 | Low | Worst-case `/query` latency is unbounded at the proxy | Provider calls time out at 30 s, 2 attempts per provider, up to 3 providers; Caddy `reverse_proxy` sets no response timeout | Read from the latency histogram (buckets to 30 s) after the load test (**pending**) |
| P4 | Low | Uploaded PDFs have no page-count or parse-time cap | `api/routers/ingest.py` checks `%PDF-`, size (10 MiB) and rate (10/min); parsing runs unbounded | Key holders only (single-user, F-19); revisit with Phase 17 multi-tenancy |
| P5 | — | Container image vulnerabilities | Trivy step added (F-22), report only | First scan result on the Trivy PR (**pending**) |

## Recommendations

- R3 (Low): `/docs`, `/redoc` and `/openapi.json` are public (FastAPI defaults; Caddy blocks only `/metrics` and `/ingest`). The repository is public, so this discloses nothing new; block them at Caddy only if the API surface should stay unadvertised.
- R4 (Low): the app container has no `read_only` root or `cap_drop: [ALL]`. It already runs as the non-root `appuser`. Optional hardening; needs writable paths for the volumes and the HF cache.
- R5 (Low): first-party GitHub and Docker actions are pinned by major tag (Dependabot keeps them current); only the third-party Trivy action is pinned by SHA. Acceptable.

## Controls implemented and verified (by reading code/config; live checks cited where they exist)

- Auth: Bearer key on every data route (`Depends(verify_api_key)`), fails closed (F-19, tests). Single-user by decision.
- Rate limits: per key and provider (`groq` 100/min), feedback 30/min, documents 10/min; fail open if Redis is down (by design).
- Upload: `%PDF-` magic check, streamed 10 MiB cap plus the Caddy 11 MiB cap, plain-name validation, injection scanner on every ingest path (soft injection INJ04 still missed: known).
- Public surface: `/metrics` and `/ingest` return 404 at Caddy (smoke-tested on every deploy); only 80/443 public; Grafana bound to 127.0.0.1; Redis and Prometheus have no host ports.
- Secrets: no secrets in the image or repo; keys rotated after the 2026-10-29 incident; deploy key least-privilege, rotation due 2027-01-27 (F-18 accepted).
- CI/CD: every workflow `contents: read` or less; only `build-push` has `packages: write`; the deploy job has `permissions: {}`; no `pull_request_target`. Deploy is health-checked and smoke-tested; rollback drilled 2026-10-29.
- Builds: locked dependencies; pip-audit weekly and on dependency PRs (chromadb/filelock advisories reviewed and ignored with reasons); torch moves to one audited pin file (15.4).
- Observability: request IDs across logs, metrics and Langfuse; per-stage tokens and latency; SLO recording rules and burn-rate email alerts; external uptime check.
- Retention: logs rotate 3 × 10 MB; feedback text 90 days; cache 24 h; Prometheus 30 days (`Data_Privacy.md`).
- Backups: both index volumes backed up and restored by hand; rehearsed 2026-11-02 (`Backup_Recovery.md`).
- Containers: non-root user, `HEALTHCHECK`, `mem_limit` on every service, `restart: unless-stopped`.

## Outcome (15.4 lite, owner decision 2026-11-07)

R1 fixed. R2–R5 and P4 accepted for a single-user system. P1–P3 accepted with the load test: capacity is derived from the Groq free tier (roadmap §15.4), and `loadtest/query.js` is kept for a later run. P5 is filled in from the first Trivy run on the image build.

## Not production-ready claims this review does not make

No load test has run yet (P1–P3), the image has not been scanned yet (P5), and generation quality since #136 has no fresh baseline. These are 15.4 work items, not controls.
