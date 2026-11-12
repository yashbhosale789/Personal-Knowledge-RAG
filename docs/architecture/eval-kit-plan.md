# Eval kit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A standalone, pip-installable `rag-eval-kit` that measures any RAG through an adapter, proven by reproducing Production RAG's retrieval baseline exactly.

**Architecture:** Copy `rag-project/eval/` modules into a new package and replace every app import with an adapter object (`retrieve`, `answer`, `version`, `corpus_id`) loaded from a `module:attr` string. Scoring and statistics code is copied unchanged; only the I/O edges change. Production gets one adapter file in this repo; the kit never imports the app.

**Tech Stack:** Python ≥ 3.11, stdlib only for the core; optional extra `[judge]` = `requests`, `numpy`, `sentence-transformers`. setuptools via `pyproject.toml`, argparse CLI, pytest.

**Spec:** `docs/architecture/eval-kit-design.md` (approved 2026-11-12).

## Global Constraints

- Kit folder `D:\Development\GenAI\rag-eval-kit\`, repo `yashbhosale789/rag-eval-kit`, import name `rag_eval_kit`, CLI `rag-eval-kit`, MIT licence.
- The kit imports nothing from this repo or from any portfolio variant. `rag-project/eval/` is not modified.
- The kit is installed into the local venv only (`pip install -e`); never added to `requirements*.txt` or the Docker image.
- $0: no task makes an LLM call except Task 7's judge, and only when the owner runs it after the call count is stated.
- The user does all git. "Commit" steps hand the user exact commands with explicit paths.
- `norm`, `basename`, `match_matrix`, `score`, `sign_test`, `bootstrap_ci`, `verdict`, `content_id`, `key`, `load`, `append`, `context_hash`, `parse_json_reply`, the three judge prompts and `is_refusal` are copied verbatim (only imports change).
- Every result record carries `dataset` (= `content_id` of the dataset file), `corpus` (= `adapter.corpus_id` or `""`) and `version` (= `adapter.version`).

## Review Focus

1. A chunk from `retrieve` missing `text` or `source` → `ValueError` naming the question id and the missing key, not a bare `KeyError` (Task 2).
2. `source` given as a full path (`C:\docs\a.pdf`, `/srv/a.pdf`) → matches the dataset's `a.pdf` (Task 2).
3. `retrieve` returns `[]` → all metrics 0.0, no crash (Task 2).
4. `retrieve` raises for one question → that record gets `"error"`, the run continues, means exclude it, and the summary prints the error count (Task 2).
5. Dataset ids not shaped like `Q01` (e.g. `faq-3`) → generation and judging order by dataset position, no `int(qid[1:])` (Tasks 6, 7).

---

### Task 1: Package skeleton, store and dataset validator

**Files:**
- Create: `rag-eval-kit/pyproject.toml`, `LICENSE` (MIT, owner's name as in this repo's git config), `.gitignore`, `src/rag_eval_kit/__init__.py`, `src/rag_eval_kit/store.py`, `src/rag_eval_kit/dataset.py`, `src/rag_eval_kit/cli.py`
- Test: `tests/test_store.py`, `tests/test_dataset.py`

**Interfaces:**
- Produces: `store.content_id(path: Path) -> str`, `store.key(variant: str, qid: str, version: str) -> str`, `store.load(path: Path) -> dict[str, dict]`, `store.append(path: Path, record: dict) -> None`, `store.context_hash(contexts: list[str]) -> str`; `dataset.norm(text: str) -> str`, `dataset.basename(path: str) -> str`, `dataset.load(path: Path) -> list[dict]`, `dataset.check(items: list[dict], chunks: dict[str, list[str]] | None) -> tuple[list[str], list[str]]` (errors, warnings); `cli.main(argv: list[str] | None = None) -> int` with subcommand `validate DATASET [--chunks FILE.jsonl]`.

- [ ] **Step 1: Write failing tests**

```python
def test_content_id_ignores_crlf(tmp_path):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    a.write_text('[{"id": "Q1"}]\n'); b.write_bytes(b'[{"id": "Q1"}]\r\n')
    assert store.content_id(a) == store.content_id(b) and len(store.content_id(a)) == 10

def test_load_skips_torn_line(tmp_path):
    p = tmp_path / "r.jsonl"; store.append(p, {"key": "k1"}); p.open("a").write('{"key": "k2"')
    assert list(store.load(p)) == ["k1"]

def test_content_id_is_key_order_independent(tmp_path):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    a.write_text('[{"id": "Q1", "x": 1}]'); b.write_text('[{"x": 1, "id": "Q1"}]')
    assert store.content_id(a) == store.content_id(b)

def test_categories_include_new():
    assert {"multi_hop", "image", "table"} <= dataset.CATEGORIES

def test_check_rejects_abstain_with_spans():
    errs, _ = dataset.check([{**VALID_ABSTAIN, "relevant": [{"source": "a.pdf", "evidence": "x" * 30}]}], None)
    assert any("abstain items must have relevant=[]" in e for e in errs)

def test_check_without_chunks_skips_span_check():
    assert dataset.check([VALID_ANSWER], None) == ([], [])
```

- [ ] **Step 2: Run `python -m pytest tests -q` in `rag-eval-kit/`** — expected: import errors.
- [ ] **Step 3: Implement.** `store.py` = the listed functions copied from `harness/store.py` (drop `ast_hash`, `code_hashes`, `fingerprint`, `run_ids`). `dataset.py` = `validate_dataset.py` with `CATEGORIES` += `"image"`, `"table"`; `load_chunks` replaced by reading a JSONL of `{"source", "text"}`; `check()` loops `check_item` and skips `check_span` when `chunks is None`. `pyproject.toml`: `requires-python = ">=3.11"`, no core dependencies, extras `judge = ["requests", "numpy", "sentence-transformers"]`, `dev = ["pytest"]`, script `rag-eval-kit = "rag_eval_kit.cli:main"`. `validate` exits 1 on errors.
- [ ] **Step 4: Run tests** — expected: all pass. Also `pip install -e .[dev]` then `rag-eval-kit validate tests/data/tiny.json` (a 2-item fixture: one answer, one abstain) — expected: exit 0. The Production dataset id `8f89d42be9` is checked in Task 4, not here (the kit ships none of this repo's data).
- [ ] **Step 5: Hand the user git commands** (`git init`, `git add` the files above, commit `feat: package skeleton, store, dataset validator`).

### Task 2: Adapter loading and retrieval metrics

**Files:**
- Create: `src/rag_eval_kit/adapter.py`, `src/rag_eval_kit/retrieval.py`; modify `cli.py`
- Test: `tests/test_retrieval.py`

**Interfaces:**
- Consumes: `dataset.norm`, `dataset.basename`, `dataset.load`, `store.content_id`.
- Produces: `adapter.load_adapter(spec: str) -> object` (`"module:attr"`; inserts `os.getcwd()` into `sys.path`; instantiates `attr` if it is a class); `retrieval.score(item: dict, ranked: list[dict], ks: tuple[int, ...]) -> dict[str, float]`; `retrieval.run(adapter, items: list[dict], ks=(1, 3, 5), dataset_id: str = "") -> list[dict]`; CLI `retrieval --adapter SPEC --dataset FILE [--split dev|test|all (default all)] [--out FILE (default runs/retrieval.json)]`.
- Record shape: `{"id", "category", "split", "question", "dataset", "corpus", "version", "metrics": {"recall@k", "success@k", "mrr"}}` or `{..., "error": str}`.

- [ ] **Step 1: Write failing tests** — port the cases in `harness/retrieval_eval.py::_selfcheck` (chunks now `{"text", "source"}`), plus:

```python
def test_full_path_source_matches():
    ranked = [{"text": "the quick brown fox", "source": r"C:\docs\a.pdf"}, {"text": "x", "source": "/srv/b.pdf"}]
    assert retrieval.score(ITEM_A, ranked, (1,))["recall@1"] == 1.0

def test_empty_ranked_scores_zero():
    assert retrieval.score(ITEM_A, [], (1, 3)) == {"recall@1": 0.0, "success@1": 0.0, "recall@3": 0.0, "success@3": 0.0, "mrr": 0.0}

def test_missing_source_names_item():
    with pytest.raises(ValueError, match="Q1.*source"):
        retrieval.run(Stub([{"text": "t"}]), [ITEM_A], (1,))

def test_adapter_error_is_recorded_and_run_continues():
    rows = retrieval.run(Raises(), [ITEM_A, {**ITEM_A, "id": "Q2"}], (1,))
    assert [r.get("error") is not None for r in rows] == [True, True]
```

- [ ] **Step 2: Run** `python -m pytest tests/test_retrieval.py -q` — expected: FAIL (module missing).
- [ ] **Step 3: Implement.** `score` and `match_matrix` verbatim; `chunk_source` becomes `basename(chunk["source"])`. `run` validates each chunk's keys before scoring (ValueError, Review Focus 1), catches other adapter exceptions per item (Review Focus 4), and only scores `expected_outcome == "answer"` items. The CLI prints means over non-error rows and the error count, and writes the JSON list.
- [ ] **Step 4: Run tests** — expected: pass.
- [ ] **Step 5: Hand the user git commands** for these files; commit `feat: adapter loading and retrieval metrics`.

### Task 3: Example that runs with no LLM

**Files:**
- Create: `examples/docs/` (2 short public-domain texts, e.g. Project Gutenberg excerpts, with source attribution in `examples/README.md`), `examples/questions.json` (5 items: 4 answer, 1 abstain), `examples/keyword_adapter.py` (class `KeywordAdapter`: splits the texts into paragraphs, ranks by word overlap, `version = "keyword-v1"`)
- Test: `tests/test_example.py`

**Interfaces:** Consumes `cli.main`, `load_adapter`.

- [ ] **Step 1: Write failing test** — `cli.main(["validate", "examples/questions.json"]) == 0` and `cli.main(["retrieval", "--adapter", "examples.keyword_adapter:KeywordAdapter", "--dataset", "examples/questions.json", "--out", str(tmp)]) == 0` with 4 records and `mrr > 0` on at least 3.
- [ ] **Step 2–4:** run (fail), write the files, run (pass).
- [ ] **Step 5: Hand the user git commands**; commit `feat: no-LLM example`.

### Task 4: Production adapter and exit check (this repo, $0)

**Files:**
- Create: `rag-project/scripts/eval_kit_adapter.py` (this repo)

**Interfaces:**
- Consumes (app side, allowed here): `eval.harness.retrieval_eval.load_rewrites`, `chunk_source`; `eval.harness.store.fingerprint`, `content_id`; `src.pipeline.advanced_rag.retrieve_context`; `src.vectorstore.store.get_vectorstore`; `config`.
- Produces: class `Production` with `version = store.fingerprint()`, `corpus_id = content_id(config.CHUNKS_PATH)`, `retrieve(question) -> [{"text", "source"}]` = `retrieve_context(rewrite, 3, None)["reranked"]` mapped with `chunk_source`.

- [ ] **Step 1: Implement.** `__init__` repeats the Chroma-vs-`chunks.json` count check from `retrieval_eval.main` and loads the rewrite cache. `retrieve` takes the rewrite from `cache["rewrites"][question]` and raises `RuntimeError("rewrite cache miss: <question>; filling it costs LLM calls, ask the owner")` on a miss. It never calls `rewrite_query`.
- [ ] **Step 2: Install the kit locally.** From `rag-project/`, in the venv used for the app: `pip install -e ..\..\rag-eval-kit`. Expected: success, no change to any requirements file.
- [ ] **Step 3: Run** from `rag-project/`: `rag-eval-kit retrieval --adapter scripts.eval_kit_adapter:Production --dataset eval/data/golden_dataset.json --out <scratchpad>/kit_prod.json`. Expected: 71 records, 0 errors, R@3 0.876, MRR 0.829, corpus `281db7190c`, dataset `8f89d42be9`.
- [ ] **Step 4: Verify item by item.** One-off check (not committed): for every id, every key in the kit's `metrics` equals `retrieval_baseline_current.json[id]["metrics"]["reranked"][key]`. Expected: `71/71 identical`. On any difference, stop and debug (superpowers:systematic-debugging); do not adjust the baseline.
- [ ] **Step 5: Hand the user git commands** for `rag-project/scripts/eval_kit_adapter.py`; commit `eval: Production adapter for rag-eval-kit; reproduces retrieval baseline`.

### Task 5: Paired comparison

**Files:** Create `src/rag_eval_kit/compare.py`; modify `cli.py`. Test: `tests/test_compare.py`.

**Interfaces:**
- Consumes: `store.load`, `store.key`, `dataset.load`.
- Produces: `compare.load_ret(path: Path) -> dict[str, dict[str, float]]` (by id, from a retrieval file), `compare.load_gen(gen_path: Path, judge_path: Path, variant: str, version: str, items: dict) -> dict[str, dict[str, float]]`, plus verbatim `sign_test`, `bootstrap_ci`, `verdict`. CLI `compare A B METRIC [--metric-b] [--split] [--family] [--min-effect] --dataset FILE` where A/B are `ret:<file>` or `gen:<variant>@<version>` (gen reads `runs/generations.jsonl`, `runs/judgments.jsonl` unless `--runs DIR`). `--company` and `--brand` are dropped (app-specific).

- [ ] **Step 1: Write failing tests** — port `harness/compare.py::_selfcheck`; plus `load_ret` on two Task 2 files with identical metrics → verdict `"no evidence of a difference at this sample size"`.
- [ ] **Step 2–4:** run (fail), implement, run (pass).
- [ ] **Step 5: Hand the user git commands**; commit `feat: paired comparison`.

### Task 6: Generation and gate

**Files:** Create `src/rag_eval_kit/generate.py`, `src/rag_eval_kit/gate.py`; modify `cli.py`. Test: `tests/test_generate.py`, `tests/test_gate.py`.

**Interfaces:**
- Consumes: `load_adapter`, `store.*`, `dataset.load`.
- Produces: `generate.is_refusal(out: dict, phrase: str) -> bool` (body verbatim, phrase a parameter, default `"don't have enough information"`); `generate.run(adapter, items, out_path: Path, variant: str = "baseline", limit: int | None = None, phrase: str = ...) -> None` writing records `{"key", "variant", "qid", "version", "dataset", "corpus", "question", "answer", "contexts", "context_hash", "outcome", "refused", "latency_ms", "ts"}` (+ `"error"`), skipping keys already stored; `gate.evaluate(items, gens, judged, variant, version, faith_floor=0.85, rel_floor=0.75)` verbatim. CLI `generate --adapter --dataset [--split] [--limit N] [--variant] [--refusal-phrase]`, `gate --dataset [--variant] --version V [--faith-floor] [--rel-floor] [--ci-only]`.

- [ ] **Step 1: Write failing tests** — port `generate._selfcheck` and `gate._selfcheck`; plus: a stub adapter over items with ids `faq-3`, `faq-1` writes records in dataset order (Review Focus 5); a rerun with the same output file makes no new `answer` calls.
- [ ] **Step 2–4:** run (fail), implement, run (pass). `generate` prints, before any call, `N adapter.answer calls will be made` and requires `--yes` when N > 0.
- [ ] **Step 5: Hand the user git commands**; commit `feat: generation and gate`.

### Task 7: Judge (any OpenAI-compatible LLM)

**Files:** Create `src/rag_eval_kit/judge.py`; modify `cli.py`. Test: `tests/test_judge.py`.

**Interfaces:**
- Consumes: `store.*`, `dataset.load`, generation records from Task 6.
- Produces: `judge.judge_call(prompt: str) -> str` posting to `$JUDGE_BASE_URL/chat/completions` with `$JUDGE_MODEL`, `Bearer $JUDGE_API_KEY` (retry and pacing logic verbatim; gap from `--min-gap`, default 4.5 s); `faithfulness`, `correctness`, `relevancy`, `applicable`, `run_metric`, `calibrate`, `parse_json_reply` verbatim; `relevancy` embeds with `--embed-model` (default `BAAI/bge-small-en-v1.5`). CLI `judge --dataset [--variants ...] --version V [--limit N] [--yes]` and `judge calibrate FILE`. `clean()` is dropped: the adapter returns clean answers. Missing `[judge]` extra → `SystemExit("pip install rag-eval-kit[judge]")`.

- [ ] **Step 1: Write failing tests** with `judge_call` monkeypatched (no network): faithfulness `{"total": 4, "supported": 3}` → 0.75; correctness bad counts → `(None, {"error": "unparsable"})` after 2 tries; pending order follows dataset position for ids `faq-3`, `faq-1`; with 0 pending, no call is made.
- [ ] **Step 2–4:** run (fail), implement, run (pass). Before any call, print `N judge calls to <model> at <base url>` and require `--yes`.
- [ ] **Step 5: Hand the user git commands**; commit `feat: LLM judge over OpenAI-compatible endpoints`.

### Task 8: README and CI

**Files:** Create `README.md`, `.github/workflows/tests.yml`.

- [ ] **Step 1: README** covering install from GitHub, the adapter contract (the design's code block), the dataset format with one example item, the quickstart from Task 3, each CLI command with one line, judge env vars, and "how to read compare output". No numbers from this repo or the portfolio.
- [ ] **Step 2: CI** runs `pip install -e .[dev]` and `python -m pytest -q` on Python 3.11 and 3.13; no secrets, no `[judge]` extra.
- [ ] **Step 3: Verify** with `python -m pytest -q` locally (pass) and by following the README quickstart in a fresh venv (exit 0).
- [ ] **Step 4: Hand the user** the commands to commit, create the GitHub repo `rag-eval-kit` (public) and push.

## After this plan (separate, each needs owner OK and cost first)

Variant adapters in `RAG - Portfolio\benchmarks\` (retrieval, $0 except Agentic if it needs an LLM) → ~20-question generation subsets, one Groq day each → 16.5 table. Roadmap §16.4 and Memory.md §2 get a status line when Task 4 passes.
