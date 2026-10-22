# RAG Project Context — Architecture and Engineering Principles
 
Last reviewed: 2026-10-19
 
## Goal
 
Build a learning-stage Personal Knowledge Base RAG application that progressively demonstrates production-grade AI engineering. The goal is not merely to produce a chatbot; it is to build a system that can be measured, secured, debugged, operated, and improved.
 
## Source-of-truth files
 
Use each project file for one purpose:
- `Roadmap.md` (or `docs/context/Roadmap.md`): phase plan and completion status.
- `Memory.md` (or `docs/context/Memory.md`): technical history, decisions, lessons, current state, and unresolved issues.
- `CLAUDE.md`: coding workflow and engineering scope discipline.
- `Ponytail.md` (or `docs/context/Ponytail.md`): lazy senior developer discipline.
When information conflicts, prefer newer verified evidence. Inspect the repository and tests before acting. Clearly distinguish confirmed facts from assumptions. Do not silently mark unresolved work as complete.
 
## Architecture direction
 
The intended RAG pipeline is conceptually:
 
```text
User
  → API and request validation
  → Query understanding / optional rewrite
  → Hybrid retrieval (dense vectors + BM25)
  → Rank fusion
  → Reranking
  → Context sufficiency assessment
  → Grounded generation
  → Citation / answer verification
  → Answer or abstention
  → Logs, metrics, traces, and evaluation
```
 
The exact live implementation may differ. Inspect the code before assuming a component, call order, interface, or behavior. Add agents, MCP, asynchronous processing, caching, and distributed components only when a real requirement justifies them.
 
## Retrieval and answer quality
 
Develop and evaluate retrieval/generation components as separate stages where practical:
- Document parsing, chunking, metadata, embeddings, and indexing.
- Dense retrieval and keyword retrieval.
- Rank fusion and reranking.
- Context selection and sufficiency checks.
- Grounded generation.
- Citation correctness and answer verification.
- Confidence handling and abstention.
- Prompt/model version management.
Useful metrics, selected according to the use case:
- Recall@K and Precision@K.
- MRR and NDCG.
- Context relevance and coverage.
- Answer correctness.
- Faithfulness/groundedness.
- Citation correctness.
- Hallucination and inappropriate-answer/abstention rates.
- Latency, throughput, token usage, and cost.
Maintain a versioned evaluation dataset that includes ordinary, difficult, ambiguous, multi-hop, unanswerable, and adversarial cases. Validate synthetic examples before adding them to the golden set. Compare variants on the same examples and report uncertainty where practical.
 
Do not treat generic numeric targets (for example, a universal recall or hallucination threshold) as standards. Set thresholds based on the use case and baseline.
 
## Grounding principles
 
- Retrieved evidence should be the source of truth for corpus-specific answers.
- Give the model an explicit instruction for what to do when evidence is insufficient.
- Make source boundaries clear and preserve metadata needed for citations.
- Prefer a correct abstention to a confident unsupported answer.
- Treat prompt-injection defenses as defense in depth; retrieved documents are untrusted input.
- Verify that citations actually support the associated claims.
## Production engineering
 
### Security
- Authentication and authorization appropriate to the deployment.
- Document-level access controls and tenant isolation when required.
- Secret management; never place credentials in source control, prompts, logs, or project memory.
- Input/output validation and safe error messages.
- Prompt-injection defenses for retrieved content and tool use.
- Auditability for sensitive operations.
- Human approval for consequential or destructive actions.
### Reliability
- Explicit timeouts.
- Bounded retries and exponential backoff where appropriate.
- Clear error handling and failure classification.
- Graceful degradation and provider fallback only when its behavior is intentional.
- Idempotency for operations that may be retried.
- Rate limiting and resource limits.
- Avoid retrying already-successful pipeline stages when only a later stage failed, where a practical design permits it.
- Observability must not become a single point of failure; tracing should fail open when appropriate.
### Observability
Track what is useful and available:
- Request/query ID.
- Pipeline stage and duration.
- Retrieval results/scores where safe.
- Model/provider and model version.
- Prompt version.
- Token usage and estimated/reported cost.
- Errors, retries, fallback, and timeouts.
- Citations, confidence/abstention outcomes.
- Evaluation results.
Infrastructure metrics and RAG quality/tracing serve different purposes. Avoid duplicating the same metric across systems without a clear reason.
 
### Cost and performance
- Measure before optimizing.
- Use caching only with correct invalidation and isolation.
- Never let permission-sensitive responses leak through shared caches.
- Optimize prompt/context size, retrieval depth, model selection, and reranking based on evaluation.
- Account for local-model memory/latency constraints.
- Treat free-tier quotas and model availability as time-sensitive facts to verify.
## Data, ingestion, and distributed systems
 
Keep expensive parsing, chunking, and embedding work in the ingestion/indexing path rather than repeating it on every query. Use background jobs, event queues, Kafka, Kubernetes, sharding, or other distributed components only when workload and reliability requirements justify their operational cost.
 
For asynchronous ingestion, consider idempotency, retries, dead-letter handling, status reporting, and recovery from partial failures.
 
## Agents, tools, and MCP
 
Use a progression from deterministic chains to tool calling and then agents only when needed. An agent should solve a concrete problem such as multi-step planning, iterative retrieval, tool selection, or human approval—not merely wrap a simple chain.
 
Compare chain/agent alternatives on quality, latency, cost, debuggability, and reliability. Treat tool inputs and outputs as untrusted; validate schemas, permissions, and results. MCP is an interoperability protocol, not a guarantee of tool safety.
 
## Model engineering experiments
 
Treat these as focused experiments rather than mandatory production dependencies:
- Transformer, attention, tokenization, context, and inference fundamentals.
- Embedding selection, similarity, normalization, and versioning.
- Loss functions and ranking objectives.
- RAG vs. fine-tuning vs. hybrid approaches.
- LoRA and quantization trade-offs.
- Mixture-of-Experts routing and active vs. total parameters.
- Reasoning decomposition and verification without exposing private chain-of-thought.
- Prompt/context compression and token optimization.
## Production definition of done
 
The system should progressively be able to:
- Retrieve only authorized evidence.
- Produce grounded answers with verifiable citations.
- Abstain when evidence is insufficient.
- Measure quality and run regression evaluations.
- Explain failures through logs/traces.
- Monitor latency, cost, and errors.
- Handle provider/service failures predictably.
- Protect data, users, and tools.
- Manage prompt/model versions and rollbacks.
- Deploy reproducibly with automated checks.
- Scale through asynchronous/distributed architecture when justified.
## Working rule
 
For every proposed technology or architectural addition, answer:
1. What concrete problem does it solve?
2. Why is it needed now?
3. How will we measure its value?
4. What complexity, cost, and failure modes does it introduce?
Prefer measurable experiments and the smallest correct design over complexity for its own sake
