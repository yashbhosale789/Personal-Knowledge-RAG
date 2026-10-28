# Eval failure analysis — dev split, 2026-10-28 (Phase 13.0 item 6)

Input to Phase 15. Read every dev question the pipeline gets wrong and bucket the cause.

## Sources and caveats

- Dataset `v1` = `dataset` id `51bcd1e330`, corpus `c1` = `corpus` id `9fc4650202` (the ids every eval record now carries).
- **Retrieval:** fresh `eval.harness.retrieval_eval` run on 2026-10-28, current code, cached rewrites, no LLM calls. Per-question metrics are identical to the previous saved baseline for all 46 answerable questions.
- **Answers and judge scores:** the saved `baseline` run at fingerprint `c83fff9ba7` (`eval/runs/generations.jsonl`, `judgments.jsonl`), 45/45 dev questions generated, 32 answered ones judged. The current fingerprint is `e7c1e5abc7`; Phase 13.2–13.4 changes since were versioning, accounting and tracing, and retrieval is unchanged, so this is representative but not a fresh generation run. No new LLM calls were spent (free-tier budget).
- Thresholds used: retrieval miss = `fused.recall@10 < 1`; ranking = fused finds it but `reranked.recall@5 < 1`; generation = answered but judge `correctness < 1` or `faithfulness < 0.8`.

## Result

34 of 45 dev questions are clean. All 8 expected-abstain questions abstained correctly; no answer was given where it should not have been. 11 questions fail:

| Q | Category | Expected → got | Primary cause | Detail |
| --- | --- | --- | --- | --- |
| Q05 | difficult | answer → abstain | **Wrong abstention — sufficiency judge** | Evidence retrieved (rr@5 = 1). Judge: "lists the step but does not explain why". Over-strict on "why" questions. |
| Q55 | adversarial | answer → abstain | **Wrong abstention — sufficiency judge** | False premise ("spare is fine for highways"). Context refutes it; judge abstained instead of correcting the premise. |
| Q56 | adversarial | answer → abstain | **Wrong abstention — sufficiency judge** | False premise (tailgate-mounted spare). Same pattern; rr@5 = 0.5. |
| Q25 | normal | answer → abstain | **Wrong abstention — score floor** | Evidence at rr@5 = 1, but top cross-encoder score −7.63 is below `SUFFICIENCY_CE_FLOOR = −7.0`. |
| Q14 | adversarial | answer → abstain | **Ranking** | Evidence not in reranked top 5 (rr@5 = 0); judge then abstained. |
| Q36 | multi_hop | answer → low-confidence answer | **Retrieval miss** | Half the evidence never retrieved (fused recall@10 = 0.5); answer lists other precautions, correctness 0, citation verifier flagged an unsupported claim. |
| Q35 | multi_hop | answer → answer | **Ranking** | Second evidence span ranked out of top 5; answer covers 1 of 2 points. |
| Q09 | difficult | answer → answer | **Generation — incomplete** | Covers 2 of 3 points; omits "drive slowly, check pressure". |
| Q43 | ambiguous | answer → low-confidence answer | **Generation — incomplete / extraction** | Covers 1 of 2 points; citation verifier flagged a sentence containing `A<U+202F>ventro` — PDF extraction splits the brand name with narrow no-break spaces. |
| Q17 | normal | answer → answer | **Possible label issue** | Answer ("unlock the lever first") vs ground truth ("adjust distance from the pedals first"); judge 0/1. Review the label before treating it as a pipeline failure. |
| Q32 | multi_hop | answer → answer | Retrieval miss (benign) | fused recall@10 = 0.5, yet the answer scored correctness 1.0. |

## Buckets (primary cause)

| Cause | Count | Questions | Phase 15 owner |
| --- | --- | --- | --- |
| Wrong abstention — LLM sufficiency judge | 3 | Q05, Q55, Q56 | 15.2 stage ablations (sufficiency judge); judge prompt for "why" questions and false premises |
| Wrong abstention — cross-encoder score floor | 1 | Q25 | 15.2 (re-tune `SUFFICIENCY_CE_FLOOR` on dev only) |
| Ranking | 2 | Q14, Q35 | 15.2 retrieval variants (reranker, candidate pool) |
| Retrieval miss | 2 | Q36 (harmful), Q32 (benign) | 15.2 retrieval variants and chunking (multi-hop) |
| Generation incomplete | 2 | Q09, Q43 | Unowned — no Phase 15 step covers answer completeness yet; add to 15.2 |
| Label to review | 1 | Q17 | 13.0 follow-up (dataset) |
| Citation | 0 primary | Q36, Q43 flagged as consequences | — |

Patterns:
- **Abstention is the largest bucket (5/11) and all of it is over-abstention, never hallucination.** Adversarial false-premise questions (Q14, Q55, Q56) are the weakest slice; the system refuses instead of correcting the premise.
- **Multi-hop is the weakest retrieval slice** (reranked recall@5 0.75); every multi-hop failure is a missing second span.
- **Brand-in-query questions rank worse** (reranked recall@5 0.69 vs 0.95 without the brand).
- **Extraction artifact:** `A<U+202F>ventro` in chunk text affects matching and citation checks; belongs with ingestion work in 15.0/15.1.

## Not covered

- The 12-question test split (frozen; final reporting only).
- 27 of the 42 synthetic questions have no review record (see Phase 13.0 item 1); their labels, Q17's in particular, may carry errors.
