# RAG Project --- Production Context

## Purpose

This project is currently a learning-stage RAG system. The long-term
goal is to evolve it into a **production-grade enterprise AI
application** while maintaining deep understanding of each component.

Claude should act as a **senior AI engineer and technical mentor**:
explain concepts and trade-offs before major implementation decisions,
avoid unnecessary complexity, and use measurable experiments to validate
improvements.

------------------------------------------------------------------------

## 1. Core Principles

-   **Correctness before complexity.** Every component must solve a
    demonstrated problem.
-   **Retrieval quality is foundational.** A stronger LLM cannot
    compensate for poor retrieval.
-   **Evaluation is part of the product.** Do not rely only on manual
    testing.
-   **Observability is mandatory.** Every request should be explainable
    and debuggable.
-   **Security and governance are architectural concerns.**
-   **Production readiness includes reliability, deployment, monitoring,
    cost control, and rollback.**
-   **Prefer evidence over assumptions.** Establish a baseline before
    optimizing.

------------------------------------------------------------------------

## 2. Target Architecture

The target system should evolve toward:

``` text
User Query
   ↓
Authentication / Authorization
   ↓
Query Understanding
   ↓
Optional Query Rewriting
   ↓
Hybrid Retrieval (Vector + BM25)
   ↓
Candidate Results
   ↓
Reranking
   ↓
Top-K Context
   ↓
Context Sufficiency Check
   ├── Insufficient → Retrieve Again / Clarify / Abstain
   ↓
Grounded LLM
   ↓
Citation Verification
   ↓
Answer Validation / Confidence
   ├── Low confidence → Abstain / Retry / Human Review
   ↓
Final Answer
   ↓
Observability + Evaluation
```

This is a **reference architecture, not a rigid pipeline**. Components
such as intent classifiers, agents, query rewriting, and multiple
verification stages should only be introduced when justified.

------------------------------------------------------------------------

## 3. RAG Retrieval

### Hybrid Search

Use both:

-   **Dense/vector retrieval** for semantic similarity and paraphrases.
-   **BM25/sparse retrieval** for exact terms, identifiers, error codes,
    names, numbers, and technical terminology.

Experiment with rank fusion methods such as **RRF** or weighted
combinations.

### Reranking

Typical flow:

``` text
Hybrid Search → Top 30–50 candidates → Cross-Encoder → Top 5–8 chunks
```

These numbers are starting points, not universal standards. Tune them
using evaluation data and balance relevance, latency, and cost.

### Context Sufficiency

Before generation, determine whether the retrieved evidence is actually
sufficient.

If evidence is weak, conflicting, or missing, the system should be able
to:

-   retrieve again
-   ask for clarification
-   or abstain

Prefer an honest abstention over an unsupported answer.

------------------------------------------------------------------------

## 4. Grounded Generation & Citations

The LLM should:

-   answer using retrieved evidence
-   avoid unsupported claims
-   preserve important qualifiers
-   cite relevant sources
-   never fabricate citations
-   abstain when evidence is insufficient

Citation verification should eventually confirm that:

1.  the cited source was actually retrieved,
2.  the source supports the associated claim,
3.  citations point to the correct document/chunk.

------------------------------------------------------------------------

## 5. Evaluation --- First-Class Capability

Build a versioned evaluation dataset containing:

``` text
query
expected documents
expected answer
acceptable sources
category / difficulty
```

Include:

-   normal questions
-   difficult questions
-   ambiguous questions
-   multi-hop questions
-   unanswerable questions
-   abstention cases
-   domain-specific terminology
-   adversarial/prompt-injection cases where appropriate

### Retrieval Metrics

Measure:

-   Recall@K
-   Precision@K
-   MRR
-   NDCG
-   Hit Rate
-   Context relevance/coverage

### Generation Metrics

Measure:

-   answer correctness
-   groundedness
-   faithfulness
-   citation correctness
-   hallucination rate
-   human-rated quality

Do **not** treat numbers such as `Recall@10 >95%` or `Hallucination <2%`
as universal production standards. Define targets based on business
requirements, risk, corpus, and user expectations.

------------------------------------------------------------------------

## 6. Evaluation Pipeline

``` text
Versioned Evaluation Dataset
        ↓
Run System
        ↓
Collect Traces
        ↓
Calculate Metrics
        ↓
Compare Against Baseline
        ↓
Regression Decision
```

Production logs can later provide additional evaluation cases, subject
to privacy and governance controls.

Synthetic data may be used to expand coverage, but generated ground
truth should be quality-checked and, where appropriate, human-validated.

------------------------------------------------------------------------

## 7. Observability

Every request should be traceable.

Capture, where appropriate:

-   request ID
-   query / rewritten query
-   retrieved document IDs
-   retrieval and reranking scores
-   selected chunks
-   model/provider/version
-   prompt version
-   token usage
-   latency by stage
-   total latency
-   estimated cost
-   citations
-   confidence/validation result
-   errors, retries, and fallbacks

Avoid indiscriminate logging of sensitive document contents or personal
data.

The system should answer:

> Why did this request fail, cost this much, or take this long?

------------------------------------------------------------------------

## 8. LLMOps

The project should eventually support:

-   prompt versioning
-   model versioning
-   model benchmarking
-   model deprecation handling
-   fallback models/providers
-   rollback
-   A/B or canary testing
-   evaluation gates
-   cost and latency tracking

Preferred lifecycle:

``` text
New Model / Prompt / RAG Change
        ↓
Offline Evaluation
        ↓
Regression Check
        ↓
Canary / A-B Test
        ↓
Gradual Rollout
        ↓
Monitor
        ↓
Rollback if necessary
```

------------------------------------------------------------------------

## 9. Reliability

Production AI systems must expect failures.

Implement where appropriate:

-   timeouts
-   retries with exponential backoff
-   rate limiting
-   graceful degradation
-   model/provider fallback
-   circuit breakers
-   idempotency
-   error handling

Retries should be bounded because they can increase both latency and
cost.

------------------------------------------------------------------------

## 10. Security & Guardrails

The production system should include:

-   authentication
-   authorization
-   RBAC/ABAC where appropriate
-   tenant/document-level access control
-   secret management
-   input/output validation
-   prompt-injection defenses
-   PII controls
-   audit logging
-   least-privilege tool access
-   rate limiting

**Critical rule:** retrieval must respect user authorization. The LLM
must never receive documents the user is not allowed to access.

For tool-using systems, destructive actions require policy checks and,
where appropriate, human approval.

Example:

``` text
AI proposes action
      ↓
Guardrail / Policy
      ↓
Human approval if required
      ↓
Tool execution
```

------------------------------------------------------------------------

## 11. Agents & Tool Use

Agents are an advanced extension, not a requirement for basic RAG.

Introduce them only when the use case requires:

-   planning
-   multi-step workflows
-   tool selection
-   external API/database interaction
-   iterative retrieval
-   memory/state
-   human-in-the-loop decisions

Possible architecture:

``` text
Query
 ↓
Intent / Router
 ↓
Planner
 ↓
Tools
 ├─ Retrieval
 ├─ Database
 ├─ APIs
 └─ Other domain tools
 ↓
Verifier
 ↓
Final Answer
```

Avoid multi-agent complexity when a deterministic workflow is
sufficient.

------------------------------------------------------------------------

## 12. Semantic Caching

Semantic caching can reduce repeated model/API calls:

``` text
Query
 ↓
Cache Lookup
 ├─ Hit → Valid Cached Response
 └─ Miss → RAG Pipeline
```

Consider:

-   similarity threshold
-   TTL/freshness
-   document changes
-   permissions
-   tenant isolation
-   cache invalidation

Measure actual cost reduction rather than assuming caching is
beneficial.

------------------------------------------------------------------------

## 13. CI/CD & Deployment

Eventually include:

### Code

-   linting
-   formatting
-   type checking
-   unit tests
-   integration tests

### AI/RAG

-   retrieval regression tests
-   evaluation tests
-   prompt regression tests
-   structured-output tests

### Security

-   dependency scanning
-   secret scanning
-   container scanning
-   authorization tests

### Deployment

-   containerized application
-   reproducible builds
-   health checks
-   smoke tests
-   evaluation gates
-   rollback

------------------------------------------------------------------------

## 14. Production Checklist

### RAG

-   [ ] Ingestion pipeline
-   [ ] Chunking + metadata
-   [ ] Embeddings
-   [ ] Vector search
-   [ ] BM25
-   [ ] Hybrid retrieval
-   [ ] Reranking
-   [ ] Context sufficiency
-   [ ] Grounded generation
-   [ ] Citations
-   [ ] Abstention

### Evaluation

-   [ ] Versioned dataset
-   [ ] Retrieval metrics
-   [ ] Generation metrics
-   [ ] Groundedness/faithfulness
-   [ ] Hallucination tracking
-   [ ] Citation verification
-   [ ] Human evaluation
-   [ ] Regression testing

### Production

-   [ ] Authentication/authorization
-   [ ] Structured logging
-   [ ] Tracing/metrics
-   [ ] Latency monitoring
-   [ ] Token/cost tracking
-   [ ] Prompt/model versioning
-   [ ] Retries/timeouts/fallbacks
-   [ ] Secrets management
-   [ ] Guardrails
-   [ ] CI/CD
-   [ ] Containerization
-   [ ] Monitoring and rollback

------------------------------------------------------------------------

## 15. Evolution Roadmap

Build incrementally:

``` text
Phase 1  → Basic RAG
Phase 2  → Hybrid Search + Reranking
Phase 3  → Grounding + Citations + Abstention
Phase 4  → Evaluation Pipeline
Phase 5  → Observability + Cost/Latency Tracking
Phase 6  → Security + Reliability
Phase 7  → LLMOps + Model Lifecycle
Phase 8  → Containerization + CI/CD + Deployment
Phase 9  → Agents / Tools where justified
```

Do not build everything simultaneously.

Every new component should answer:

> **What production problem does this solve, and how will we prove that
> it improved the system?**

------------------------------------------------------------------------

## 16. Guidance for Claude

When developing this project:

1.  Explain important concepts before implementation.
2.  Explain **why** a component is needed.
3.  Discuss trade-offs: quality, latency, cost, complexity,
    maintainability.
4.  Establish a baseline before optimization.
5.  Use experiments and evaluation to justify changes.
6.  Avoid unnecessary abstractions and agents.
7.  Treat prompts, models, configurations, and evaluation datasets as
    versioned artifacts.
8.  Prefer production-ready practices, but introduce them progressively.
9.  Challenge architectural decisions when evidence suggests a simpler
    solution.
10. Always consider failure, security, observability, cost, and
    rollback.

The project should demonstrate:

``` text
Data
 + Retrieval
 + Reranking
 + Generation
 + Evaluation
 + Observability
 + Security
 + Reliability
 + Cost Optimization
 = Production AI Engineering
```

The objective is **not merely to build a chatbot**.

The objective is to build an AI system whose behavior can be **measured,
debugged, evaluated, secured, reproduced, optimized, and safely operated
in production**.
