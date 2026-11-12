# Eval kit — design (Phase 16.4, 2026-11-12)

Status: approved by the owner 2026-11-12 ("you decide", then "OK"). Built; exit check passed (71/71 identical). Calls marked **(Claude's call)** were delegated by the owner ("you decide") and can be overruled.

## Why

`rag-project/eval/` measures this app well (retrieval metrics, LLM judge, paired comparison, CI gate), but it imports the app directly, so nothing else can use it. 16.4 extracts a generic copy that any RAG system can plug into, so the 16.5 table comes from one code path, and outside developers can measure their own RAG with the same method.

## Who it is for

An outside developer with a working Python RAG, their own documents, and at most a free LLM key. They have no labelled question set yet. **(Claude's call)**

## Goals

- `pip install git+https://github.com/yashbhosale789/rag-eval-kit` and evaluate any RAG through a small adapter.
- Same metrics and maths as `rag-project/eval/`, copied, not rewritten.
- Every result record carries the dataset id, the corpus id and the adapter's version string.
- Exit check: Production RAG through the kit reproduces its retrieval baseline exactly.

## Non-goals (v1)

- Generating questions with an LLM (`generate_candidates.py` stays in this repo only).
- PyPI publishing, a web dashboard, app-specific stage metrics (dense, BM25, fused). The kit sees only the final ranked list.
- Re-measuring Multimodal RAG (frozen; its own answer key only, roadmap 16.3/16.5).

## Anti-goals

- The kit imports anything from this app or from a portfolio variant.
- A number in the kit differs from the in-repo harness for the same inputs.
- Any paid call. Free tiers only; every LLM run states its call count first.

## Where it lives (Claude's call)

- Folder `D:\Development\GenAI\rag-eval-kit\` (sibling of this repo, outside `RAG - Portfolio\`), GitHub repo `yashbhosale789/rag-eval-kit`, import name `rag_eval_kit`, CLI `rag-eval-kit`, MIT licence.
- `rag-project/eval/` stays unchanged. Production's adapter is one new file outside it: `rag-project/scripts/eval_kit_adapter.py`. The kit is installed locally only (`pip install -e ..\rag-eval-kit`), never in `requirements*.txt` or the prod image.

## The adapter

A Python object named on the command line as `module:attr`:

```python
class Adapter:
    version: str          # what the user changed; part of every result key
    corpus_id: str = ""   # optional; recorded, not checked
    def retrieve(self, query: str) -> list[dict]:   # ranked; each {"text", "source", "page"?}
    def answer(self, query: str) -> dict:           # {"answer", "contexts": [str]}; generation only
```

Page is optional: the dataset labels match on `source` + an evidence phrase in the chunk text, not on pages or chunk ids, so any chunking works (checked: `relevant` = `{source, evidence}`). The adapter does its own query rewriting, answer cleaning (citation markers, caveats) and refusal wording. The kit never knows about them.

## Contents, mapped from `rag-project/eval/`

| Kit module | From | Change |
|---|---|---|
| `dataset.py` | `tools/validate_dataset.py` | schema + enums kept; span check takes an optional `--chunks` JSONL instead of `config.CHUNKS_PATH`; categories gain `image`, `table` (`multi_hop` already exists) |
| `retrieval.py` | `harness/retrieval_eval.py` | keep `norm`, `basename`, `match_matrix`, `score` byte-for-byte; ks 1/3/5 + MRR; drop stages, tokenizers, rewrites, index check |
| `generate.py` | `harness/generate.py` | calls `adapter.answer`; keep record shape and `is_refusal` (refusal phrase becomes an option); drop ablations, `f29`, token accounting from the app |
| `judge.py` | `harness/judge.py` | same three prompts; `calibrate` reads the user's own labelled file (this repo's `judge_calibration.json` is not shipped); LLM via any OpenAI-compatible endpoint (`JUDGE_BASE_URL`, `JUDGE_MODEL`, `JUDGE_API_KEY`); `sentence-transformers` an optional extra `[judge]` |
| `compare.py` | `harness/compare.py` | takes two result files by path; maths unchanged |
| `gate.py` | `harness/gate.py` | floors as options (defaults 0.85 / 0.75) |
| `store.py` | `harness/store.py` | keep `content_id`, `key`, `load`, `append`, `context_hash`; the fingerprint becomes the adapter's `version` |
| `examples/` | new | a 5-question dataset over 2 small public-domain texts and a toy keyword adapter, so a first run needs no LLM |

Each module keeps its `_selfcheck()`; they run under `pytest` in the kit's CI.

## Exit check (retrieval, $0)

`rag-project/scripts/eval_kit_adapter.py`: `retrieve(q)` = `get_rewrite(q, load_rewrites())` (cached, no LLM call when the cache matches) → `retrieve_context(q, 3, None)["reranked"]`; `version` = `store.fingerprint()`; `corpus_id` = `content_id(config.CHUNKS_PATH)`; it keeps the Chroma-vs-`chunks.json` count check.

Pass = for all 71 answerable items, the kit's recall@1/3/5 and MRR equal the `reranked` metrics in `eval/runs/retrieval_baseline_current.json` item by item (means R@3 0.876, MRR 0.829), corpus `281db7190c`. The dataset id will read `8f89d42be9`, not the file's `a831d87d09`: checked 2026-11-12, the two datasets differ only in the `ci` flag of Q12/Q13, which no metric reads. If the rewrite cache misses, stop and state the call count before any LLM call.

## After the exit check

1. Retrieval re-measure of Naive, Advanced and Agentic through the kit ($0, except Agentic if its retrieval needs an LLM: count stated first).
2. Generation on a small subset (~20 dev questions) per variant, one Groq quota day each, costs stated first.
3. 16.5 table.

## Left to the builder

File layout inside the package, CLI flag names, the example texts, CI workflow details, README wording.

## Open for the owner

- Naive, Advanced and Agentic adapters live in a new folder `D:\Development\GenAI\RAG - Portfolio\benchmarks\` (one file each, loading the variant by path); the variant repos stay untouched. (Claude's recommendation, taken with the owner's OK; confirm before step 1 of "After the exit check".)
