# RAG Evaluation

## Purpose
Measure retrieval quality and answer quality separately, track regressions, and make model/prompt/reranker comparisons reproducible.

## Dataset
Document:
- Dataset file and schema.
- Dataset version.
- Question/source provenance.
- Expected evidence or answer criteria.
- Retrieval-relevance labels and reviewer process.
- Synthetic versus human-reviewed items.
- Sensitive-data checks.

## Metrics to consider
Choose metrics based on the task and verify their definitions before use:
- Retrieval: Recall@k, Precision@k, MRR, nDCG, or suitable alternatives.
- Answer: correctness, faithfulness/groundedness, relevance, citation/evidence support.
- Operations: latency, failures, token use, and estimated cost.

## Experimental protocol
- Record dataset version, code revision, prompt version, model/provider, embedding model, retrieval parameters, reranker, and run timestamp.
- Compare candidates on the same cases.
- Prefer paired comparisons and report sample size and uncertainty.
- Make runs batchable/resumable when provider quotas require it.
- Keep evaluation results and configuration together.
- Re-run evaluation after token/context optimizations.

## Current known checkpoint
A 2026-10-19 note reported 40 Chroma chunks across 5 PDFs and a successful validation of Q01 v2 using `eval/tools/validate_dataset.py`. Verify this state before treating it as current; it does not prove full evaluation coverage or phase completion.

## Acceptance thresholds
Set thresholds from observed baseline and project requirements. Do not invent passing scores or imply that a metric alone proves production readiness.
