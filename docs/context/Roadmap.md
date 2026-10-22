# Personal Knowledge OS — RAG Project Roadmap
 
Last reconciled: 2026-10-22  
Current phase: **Phase 13 — LLMOps**  
Active development copy: `rag-project/`
 
## How to use this roadmap
 
- This file defines the planned sequence of work and the status of each phase.
- Use `Memory.md` for technical history, decisions, lessons, and open issues.
- Use `Architecture.md` for stable architecture and production-quality principles.
- Follow `Ponytail.md` for lazy senior developer discipline (YAGNI, root cause, shortest working diff).
- Follow `CLAUDE.md` for coding workflow and scope discipline.
- Treat statuses as verified only when supported by code, tests, logs, or explicit user confirmation. Do not mark work complete merely because it was discussed.
- Inspect the current repository before proposing code changes. If this roadmap conflicts with verified current code or newer confirmed decisions, flag the conflict and reconcile it rather than silently guessing.

## Project goal
 
Build a production-oriented Personal Knowledge Base RAG system that demonstrates strong AI engineering and software engineering judgment: retrieval quality, grounded answers, evaluation, security, reliability, observability, deployment, and controlled operational improvement.
 
## Completed phases
 
### Phase 1 — Naive RAG
Complete. See project history and repository for implementation details.
 
### Phase 2 — Advanced RAG
Complete. Advanced retrieval and query-processing capabilities were introduced progressively.
 
### Phase 3 — Agentic RAG foundations
Complete as a learning/project milestone. Later agentic work should be introduced only when justified by a concrete use case.
 
### Phases 4–6 — RAG improvements and local model/provider work
Complete. Includes the documented local Ollama integration and provider-handling decisions. Refer to the consolidated project memory for implementation specifics.
 
### Phase 7 — Prometheus observability
Complete. Prometheus/Grafana are used for infrastructure/application metrics. RAG quality metrics and detailed token/cost tracing are tracked separately in the LLMOps work.
 
### Phase 8 — RAG quality
Complete. Includes context sufficiency, citation verification, confidence/abstention behavior, and related quality work. Verify implementation in the repository before changing it.
 
### Phase 9 — Security and reliability
Complete. Includes Redis rate limiting and semantic caching, prompt-injection defenses, and request/response validation. Known deferred issues are listed in the consolidated project memory.
 
### Phase 10 — Containerization and CI/CD
Complete. Docker/Compose and the CI evaluation gate were verified. Grafana is optional and should not need to run continuously in production.
 
### Phase 11 — Pre-deployment hardening
**Complete (verified).** Full-codebase security and reliability review; `ruff` and `bandit` hard gates in CI; `add_chunks` append-not-upsert idempotency fix in `store.py`; CI eval gate's abstention blind spot closed.
 
### Phase 12 — Deployment
**Complete / closed (verified live on AWS EC2).**
 
Verified deployment work includes:
- AWS EC2 deployment using Docker Compose.
- Caddy reverse proxy providing automated HTTPS.
- GitHub Actions build/push and deployment workflow.
- AWS Systems Manager (SSM) Run Command automated deployment (`rag-deploy` document).
- Deployment script validation (`deploy/deploy.sh`), warm-up, pull-failure handling, and rollback drill tested.
- GitHub Actions path filtering (`rag-project/**`, workflow files) and optional Grafana profile.
- Deployment and rollback behavior verified live.
Do not reimplement or revisit completed deployment work without a specific bug, operational need, or user request.
 
## Current phase
 
# Phase 13 — LLMOps
 
Phase 13 is divided into focused subphases. Prefer one substantial subphase per conversation, then record verified results and open work before starting the next one.
 
### Phase 13.0 — Evaluation foundation
**Current status: In progress; confirm the exact latest subtask before continuing.**
 
Goals:
- Maintain a versioned golden evaluation dataset covering normal, difficult, ambiguous, multi-hop, unanswerable, and adversarial queries.
- Grow the dataset toward approximately 50–60 validated questions.
- Add retrieval-relevance labels.
- Validate synthetic questions manually before treating them as golden cases.
- Build a repeatable evaluation harness that compares variants on the same questions.
- Report uncertainty/confidence intervals where appropriate.
- Keep evaluation runs resumable/batchable and avoid unnecessary LLM calls.
Known snapshot:
- Current corpus contains 40 chunks across 5 PDFs.
- `eval/validate_dataset.py` passed for Q01 v2 format against `storage/chunks.json`.
- These facts do **not** mean all Phase 13.0 goals are complete. Inspect the repository and the latest memory notes to establish the exact remaining work.

### Phase 13.1 — Token and cost accounting
Track token usage and estimated cost by pipeline stage where provider data permits. Keep missing/estimated usage clearly distinguished from provider-reported usage.
 
### Phase 13.2 — Prompt versioning
- Store prompts in the repository.
- Include a prompt-version identifier in relevant responses, logs, metrics, and cache namespaces.
- Do not introduce an external prompt-management platform unless explicitly approved and justified.

### Phase 13.3 — Reranker/model benchmarking
Use the evaluation harness to compare candidate rerankers/models against the current baseline. Report quality, latency, cost, and operational trade-offs. Retrieval metrics such as Recall@K, MRR, and NDCG do not require LLM-as-judge calls.
 
### Phase 13.4 — LLM tracing
- Langfuse was preferred over LangSmith on cost grounds.
- Langfuse Cloud Hobby was proposed, but **confirm the choice and verify current terms with the user before implementation**.
- Self-hosting is not practical on the current hardware.
- Tracing must be non-blocking and fail-open: an observability outage must not break query serving.

### Phase 13.5 — Token optimization
Evaluate each optimization against the same evaluation baseline. Report quality regressions as well as latency/cost improvements; do not optimize tokens at the expense of answer quality without an explicit trade-off decision.
 
### Phase 13.6 — Human feedback endpoint
Deferred to Phase 16 unless priorities change.
 
### LLMOps operating constraints
- Budget target: $0 unless the user explicitly approves otherwise.
- Groq free-tier TPM limits apply.
- A `/query` request can invoke multiple LLM stages, including rewriting, sufficiency judging, generation, and citation verification.
- Prefer offline paired comparisons over online A/B tests while there is insufficient production traffic to split.
- Do not assume old provider quotas or model availability remain current; verify them when the decision depends on them.

## Later roadmap — preserve the order, confirm scope before starting
 
The following are planned future directions, not current commitments to implement everything. Introduce each only when it adds demonstrable value and confirm scope where noted.
 
### Phase 14 — Graph RAG + Multimodal RAG
Planned as a **separate standalone project**, not built inside the current Personal Knowledge OS repository. Confirm scope before starting. Potential technologies include LangChain, LangGraph, LlamaIndex, and Langfuse, selected based on the actual requirements.
 
### Phase 15 — Portfolio extraction
Organize selected work into portfolio-ready standalone artifacts and shared utilities only where justified. Preserve existing phase snapshots as standalone portfolio artifacts; do not casually modify them after snapshotting.
 
### Phase 16 — React frontend and human feedback
Frontend work was intentionally deferred until later. Human-feedback endpoint work is currently deferred here as well.
 
### Later engineering tracks
Kafka/event-driven ingestion, Kubernetes, MCP/tool integration, multi-agent systems, and ML/model-engineering experiments remain future learning tracks. Prioritize based on a concrete engineering problem, portfolio value, and available time—not because a technology is fashionable.
 
## Definition of phase completion
 
Before closing a subphase:
1. Verify the implementation in the repository.
2. Run relevant tests/evaluation checks and report their actual results.
3. Record important decisions and rejected alternatives.
4. List unresolved issues without implying they are fixed.
5. Update this roadmap's status.
6. Update the consolidated project memory with concise, durable findings.
7. Provide a ready-to-use prompt for the next substantial subphase.
