# RAG Project Context — Prototype → Production

## Goal
This is a learning-stage RAG application that should progressively become a **production-grade AI/RAG system**.

Claude should act as a senior AI engineer/mentor: explain important decisions and trade-offs, prefer simple production-ready designs, avoid unnecessary complexity, and challenge additions that do not solve a real problem.

**For every technology ask:** What problem does it solve? Why is it needed? How will we measure its value? What complexity/failure modes does it add?

## Target Architecture
```text
User
 → AuthN/AuthZ
 → Query Understanding / optional Rewrite
 → Hybrid Retrieval (Vector + BM25)
 → Reranking
 → Context Sufficiency
 → Grounded LLM
 → Citation/Answer Verification
 → Confidence → Answer / Abstain / Human Review
 → Logging + Metrics + Evaluation
```
Agents, MCP, caching, async processing, etc. are optional modules introduced only when justified.

## RAG / AI Quality
Build progressively:
- ingestion → chunking → metadata → embeddings → vector DB
- BM25 + vector hybrid search
- reranking
- context engineering / selection
- grounded generation
- citations + citation verification
- confidence + abstention
- prompt/version management
- structured outputs

Evaluate:
- Recall@K / Precision@K
- MRR / NDCG
- context relevance/coverage
- answer correctness
- groundedness / faithfulness
- citation correctness
- hallucination rate
- human feedback
- latency and cost

Maintain a versioned eval dataset with normal, difficult, ambiguous, multi-hop, unanswerable and adversarial cases. Synthetic data may expand it but must be validated.

**Do not treat example targets such as >95% recall or <2% hallucination as universal standards; derive thresholds from the use case.**

## Production Engineering

### Backend & Security
- proper backend/API
- authentication + authorization/RBAC
- document-level access control
- tenant isolation where required
- secret management
- input/output validation
- prompt-injection protection
- audit logging
- human approval for sensitive/destructive actions

### Reliability
- timeouts
- retries + exponential backoff
- error handling
- graceful degradation
- model/provider fallback
- idempotency
- rate limiting

### Observability
Every request should be traceable:
```text
request → retrieval → reranking → LLM → answer
```
Track where appropriate:
- request/query IDs
- retrieved sources and scores
- model/provider/version
- prompt version
- token usage
- stage/total latency
- cost
- errors/retries/fallbacks
- citations/confidence
- evaluation results

### Cost / Performance
Learn and apply:
- caching / semantic caching
- Redis
- token optimization
- database/vector indexing
- resource optimization

Never allow permission-sensitive responses to leak through shared caches.

## Async / Distributed Architecture
Add when scale/workload requires it:
- **Docker** — containerization/reproducible deployment
- **CI/CD** — tests + RAG evals + security + deployment
- **Redis** — caching, rate limiting, temporary state
- **Kafka + EDA** — asynchronous ingestion/events
- **Kubernetes** — orchestration/scaling
- **Sharding** — advanced horizontal scaling only when justified

Example:
```text
Upload → Event → Parse → Chunk → Embed → Index → Ready
```
Learn Kafka topics, partitions, consumer groups, offsets, retries, DLQ and idempotent consumers.

## Agentic AI
Introduce only after strong core RAG:
```text
Prompt Chain
 → Tool Calling / MCP
 → Single Agent
 → Planner + Tools + Verifier
 → Multi-Agent System
```
Use agents for genuine needs: planning, multi-step workflows, tool selection, iterative retrieval, external systems, memory/state, or human approval.

Compare chain vs single-agent vs multi-agent using quality, latency, cost and reliability.

MCP is a tool interoperability layer; learn schemas, discovery, permissions, invocation and result validation.

## ML / Model Engineering Track
Run these as focused experiments, not forced production dependencies:
- **LLM fundamentals:** transformers, attention, tokens, context, inference
- **Embeddings:** similarity, dimensions, normalization, selection/versioning
- **Loss functions:** MSE/MAE, cross-entropy, contrastive/ranking losses
- **Linear regression:** ML foundations and optional quality/confidence prediction
- **LoRA:** RAG vs fine-tuning vs RAG+fine-tuning
- **Quantization:** memory/latency/quality trade-offs
- **MoE:** routing, sparse activation, experts, active vs total parameters
- **Reasoning/CoT:** decomposition and verification; do not expose private chain-of-thought
- **Token optimization:** context pruning, prompt compression, chunk selection, caching

## LLMOps / Lifecycle
Treat prompts and models like versioned software:
```text
Change → Offline Evaluation → Regression Check
       → Canary/A-B → Monitor → Rollout/Rollback
```
Cover model selection, versioning, deprecation, fallback, rollback, prompt management, cost controls and evaluation gates.

## Production Definition of Done
The system should eventually:
- retrieve only authorized evidence
- answer with grounded, verifiable citations
- abstain when evidence is insufficient
- measure and regression-test quality
- explain/debug failures through logs/traces
- monitor latency, cost and errors
- handle model/service failures
- protect users, data and tools
- support prompt/model lifecycle management
- deploy reproducibly with Docker + CI/CD
- scale through async/distributed architecture when justified

**Goal:** not another chatbot, but an AI system that can be trusted, measured, secured, operated and improved in production.

## Learning Progression
```text
Basic RAG
 → Hybrid Retrieval
 → Reranking
 → Grounding/Citations
 → Evaluation
 → Observability
 → Security/Reliability
 → Caching/Redis
 → Docker/CI-CD
 → Kafka/EDA
 → Kubernetes
 → MCP/Tools
 → Agents/Multi-Agent
```
LoRA, quantization, ML fundamentals and MoE run alongside this as model-engineering experiments.
