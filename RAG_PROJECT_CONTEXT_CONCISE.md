# RAG Project — Production-Ready Evolution Context

## Purpose

This is a **learning-focused RAG project** that will progressively evolve into a **production-grade enterprise AI application**.

Claude should act as a **senior AI engineer and technical mentor**. Explain important concepts, design decisions, trade-offs, and failure modes before significant implementation. Prefer practical, production-ready solutions without unnecessary complexity.

The goal is not a feature-heavy demo. The goal is to learn how to build an AI system that is **measurable, grounded, observable, secure, reliable, cost-aware, reproducible, and deployable**.

---

## 1. Core Principles

- Correctness before complexity.
- Every component should solve a demonstrated problem.
- Establish a baseline before optimizing.
- Measure quality, latency, cost, and reliability.
- Retrieval quality is foundational; a larger LLM does not compensate for poor retrieval.
- Evaluation is a first-class engineering artifact.
- Security, authorization, observability, and governance are architectural concerns.
- Version prompts, models, configurations, and evaluation datasets.
- Do not treat arbitrary metric targets as universal production standards.
- Prefer the simplest architecture that satisfies requirements.

For every new technology, ask:

1. What problem does it solve?
2. Why is it better than the simpler alternative?
3. How will we measure whether it helped?
4. What complexity/failure modes does it introduce?

---

## 2. Target Architecture

```text
User
  ↓
Authentication / Authorization
  ↓
Query Understanding
  ├─ Optional Intent Classification
  └─ Optional Query Rewriting
  ↓
Hybrid Retrieval
  ├─ Dense / Vector Search
  └─ Sparse / BM25
  ↓
Candidate Pool
  ↓
Reranking
  ↓
Top-K Context
  ↓
Context Sufficiency
  ├─ Insufficient → Retry / Clarify / Abstain
  ↓
Grounded LLM
  ↓
Citation Verification
  ↓
Answer Validation / Confidence
  ├─ Low confidence → Abstain / Retry / Human Review
  ↓
Final Answer
  ↓
Observability / Evaluation / Audit
```

This is a **reference architecture**, not a requirement that every request execute every step. Add agents, classifiers, rerankers, caching, etc. only when their value is demonstrated.

---

## 3. RAG Pipeline

Target flow:

```text
Query
 → Optional Query Rewriting
 → Hybrid Search (Vector + BM25)
 → Candidate Pool
 → Cross-Encoder Reranking
 → Top-K Chunks
 → Context Sufficiency
 → Grounded Generation
 → Citation Verification
 → Answer / Abstain
```

Starting points such as **30–50 retrieval candidates and 5–8 final chunks** are experimental defaults, not universal standards.

### Retrieval

Study/evaluate:

- chunking and metadata
- embeddings
- vector search
- BM25
- hybrid search / rank fusion
- metadata filtering
- reranking

Metrics:

- Recall@K
- Precision@K
- MRR
- NDCG
- Hit Rate
- context relevance/coverage

### Grounding & Citations

The LLM should use retrieved evidence as the source of truth, avoid unsupported claims, preserve qualifiers, and abstain when evidence is insufficient.

Citation verification should confirm that:

- sources exist
- cited chunks were retrieved
- claims are supported
- citations are not fabricated

### Confidence / Abstention

Confidence should combine meaningful signals such as retrieval/reranker scores, evidence coverage, validation, and citation support. Do not blindly trust an LLM-generated confidence number.

```text
High → Answer
Medium → More retrieval / caveat
Low → Abstain / clarify / human review
```

---

## 4. Evaluation

Evaluation is a core production capability.

### Retrieval

Measure:

- Recall@K
- Precision@K
- MRR / NDCG
- context relevance
- context coverage

### Generation

Measure:

- answer correctness
- groundedness
- faithfulness
- citation correctness
- hallucination rate
- human-rated quality

Also track latency, cost, token usage, reproducibility, and regression after changes.

### Evaluation Dataset

Maintain a versioned dataset containing:

```text
query
expected documents
expected/acceptable answer
acceptable sources
category
difficulty
```

Include normal, difficult, ambiguous, multi-hop, exact-term, unanswerable, abstention, and adversarial/prompt-injection cases where relevant.

Synthetic data can expand coverage but must be quality-checked.

### Evaluation Pipeline

```text
Dataset
 → Run System
 → Collect Traces
 → Calculate Metrics
 → Compare With Baseline
 → Regression Decision
```

Evaluation should eventually be part of CI/CD.

---

## 5. Observability / LLMOps

Trace production requests with appropriate:

```text
request ID
query / rewritten query
retriever configuration
retrieved IDs and scores
selected chunks
model/provider/version
prompt version
token usage
stage + total latency
cost
answer/citations/confidence
errors/retries/fallbacks
evaluation results
```

Avoid indiscriminate logging of sensitive content.

LLMOps should support:

- model/prompt versioning
- provider/model fallback
- deprecation handling
- rollback
- A/B or canary testing
- evaluation gates
- cost tracking

```text
Change → Offline Eval → Regression Check
       → Canary/A-B → Monitor → Rollout/Rollback
```

### Cost / Token Optimization

Track input/output/context tokens, embedding and reranker calls, retries, fallback usage, cache hits/misses, and cost/request.

Optimize for **quality + latency + cost**, not token count alone.

---

## 6. Reliability

Implement as appropriate:

- timeouts
- retries with exponential backoff
- circuit breakers
- graceful degradation
- fallback models/providers
- idempotency
- asynchronous error handling

Do not retry blindly; retries can increase latency and cost.

---

## 7. Caching, Redis and Rate Limiting

Use caching where measurable value exists:

```text
Embedding Cache
Retrieval Cache
Semantic Cache
LLM Response Cache
```

Study TTL, invalidation, cache consistency, cache stampede, permission-aware caching, and hit rate.

Redis can support:

- caching
- distributed rate limiting
- temporary workflow state
- distributed locks where justified

Never share sensitive/user-specific cached responses across unauthorized users.

Implement API rate limiting using techniques such as token bucket or sliding window.

---

## 8. Security and Guardrails

Authorization must happen **before retrieval/context construction**:

```text
User → Permissions → Authorized Retrieval → LLM Context
```

Include:

- authentication
- authorization / RBAC
- tenant isolation where relevant
- secret management
- encryption
- audit logging
- rate limiting
- input/output validation
- prompt-injection defenses
- PII controls
- least-privilege tool access

Destructive SQL/tool operations must be validated and protected by policy and, where appropriate, human approval.

---

## 9. Agents, Tools and MCP

Agents are an advanced extension, not a prerequisite for RAG.

Introduce them when the use case needs planning, multi-step workflows, tool selection, iterative retrieval, external systems, memory/state, or human approval.

```text
User
 ↓
Planner
 ├─ Retrieval Tool
 ├─ Database Tool
 ├─ API Tool
 └─ Other Tools
 ↓
Verifier
 ↓
Grounded Response
```

### MCP

Use MCP as a tool interoperability layer when external tools are introduced. Learn discovery, schemas, structured invocation, permissions, authentication, result validation, and failures.

### Prompt Chaining

Compare deterministic chains with agents:

```text
Analyze → Rewrite → Retrieve → Synthesize → Verify
```

Choose the simplest approach that works.

### Multi-Agent Systems

Introduce only after the core system is stable. Compare:

```text
Single Agent
vs Prompt Chain
vs Multi-Agent
```

using quality, cost, latency, and reliability.

---

## 10. Production Infrastructure

### Docker — Core

Containerize the application and supporting services. Learn multi-stage builds, image optimization, configuration/secrets, health checks, non-root containers, and reproducible builds.

### Kubernetes — Advanced

Add after Docker and operational basics are sound. Study Deployments, Services/Ingress, ConfigMaps/Secrets, probes, resource limits, scaling, rolling deployments, and observability.

### Kafka + Event-Driven Architecture — Advanced

Use Kafka for asynchronous workflows such as document ingestion:

```text
Upload
 → DocumentUploaded
 → Parse
 → Chunk
 → Embed
 → Index
 → DocumentIndexed
```

Learn topics, partitions, consumer groups, offsets, delivery semantics, retries, dead-letter topics, and idempotent consumers.

### Database Indexing — Core

Study B-tree/composite indexes, query plans, selectivity, metadata indexes, and vector indexes.

### Sharding — Advanced

Study only after understanding single-database limits: shard keys, distribution, hot partitions, cross-shard queries, and tenant/data partitioning.

### CI/CD — Core

```text
Commit
 → Lint / Type Check
 → Unit Tests
 → Integration Tests
 → RAG Evaluation
 → Security Scans
 → Build Image
 → Deploy
 → Smoke Tests
```

---

## 11. ML / Model Engineering Learning Modules

These should be focused experiments, not artificial RAG dependencies.

### LLM Fundamentals

Understand transformers/attention, tokenization, context windows, inference, temperature/top-p, structured output, tool calling, limitations, and quality/latency/cost trade-offs.

### Embeddings

Study vector representations, cosine/dot-product similarity, dimensions/normalization, model selection, multilingual/domain embeddings, and versioning/drift.

### Loss Functions

Learn MSE/MAE, cross-entropy, contrastive loss, and ranking losses; connect them to retrieval, reranking, classification, and fine-tuning.

### Linear Regression

Use as an ML foundation and optionally experiment with predicting system quality/confidence from retrieval/reranker/query features.

### LoRA / Fine-Tuning

Run:

```text
RAG only
vs Fine-tuned model
vs RAG + Fine-tuned model
```

Benchmark quality, latency, memory, and cost.

### Quantization

Experiment with lower-precision models and measure model size, RAM/VRAM, latency, throughput, and quality.

### MoE

Study routing, sparse activation, expert specialization, active vs total parameters, and load balancing. Do not add MoE merely for complexity.

### Token Optimization

Study context pruning, prompt compression, chunk selection, shorter prompts, structured outputs, model selection, and caching.

### Chain-of-Thought

Study reasoning/decomposition conceptually. Do not design the production system around exposing private chain-of-thought; prefer structured, verifiable intermediate outputs.

---

## 12. Learning Roadmap

```text
1.  Basic RAG
2.  Embeddings + Vector DB
3.  Hybrid Search
4.  Reranking + Context Engineering
5.  Grounding + Citations + Abstention
6.  Evaluation + Regression Testing
7.  Observability + Cost + Token Optimization
8.  Caching + Redis + Rate Limiting
9.  Security + Reliability + CI/CD
10. Docker + Production Deployment
11. Kafka + EDA
12. Kubernetes + Scaling
13. MCP + Tools
14. Prompt Chaining + Agents
15. Multi-Agent Systems where justified
```

Run LoRA, quantization, loss-function, regression, and MoE experiments in parallel as ML/model-engineering modules.

---

## 13. Production Definition of Done

The project should eventually demonstrate that it can:

- retrieve relevant **authorized** information reliably
- generate grounded answers
- provide trustworthy citations
- abstain when evidence is insufficient
- evaluate retrieval and generation quality
- detect regressions
- trace/debug individual requests
- track latency and cost
- handle model/provider failures
- protect data and tools
- support controlled model/prompt changes
- deploy reproducibly
- operate with monitoring and alerts

The final project should demonstrate **AI engineering maturity**, not simply LLM usage.

```text
Data
 + Retrieval
 + Reranking
 + Generation
 + Evaluation
 + Observability
 + Security
 + Reliability
 + Governance
 + Cost Optimization
 + Infrastructure
 = Production AI System
```

Every architectural addition should answer:

> **What production problem does this solve, and how will we prove that it improved the system?**
