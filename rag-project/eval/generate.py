import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

import store
from retrieval_eval import get_rewrite, load_rewrites
from validate_dataset import DEFAULT_DATASET

import config
from src.pipeline.advanced_rag import (
    retrieve_context,
    run_advanced_rag_pipeline,
)

RESULTS_PATH = Path(__file__).parent / "generations.jsonl"
REFUSAL_PHRASE = "don't have enough information"


def is_refusal(out: dict) -> bool:
    answer = " ".join(out["answer"].lower().replace("\u2019", "'").split())
    return (
        out.get("outcome") == "abstain"
        or not out.get("contexts")
        or REFUSAL_PHRASE in answer
    )


def run_pipeline(question: str, rewrite: str) -> dict:
    for attempt in range(3):
        try:
            return run_advanced_rag_pipeline(
                question, return_contexts=True, rewritten=rewrite
            )
        except requests.exceptions.HTTPError as e:
            if e.response.status_code != 429 or attempt == 2:
                raise
            time.sleep(
                min(
                    float(e.response.headers.get("retry-after") or 60 * (attempt + 1)),
                    300,
                )
            )


def to_record(
    variant: str, item: dict, fp: str, rewrite: str, out: dict, latency_ms: int
) -> dict:
    contexts = out.get("contexts", [])
    return {
        "key": store.key(variant, item["id"], fp),
        "variant": variant,
        "qid": item["id"],
        "fp": fp,
        "provider": config.PIPELINE_PROVIDER,
        "question": item["question"],
        "rewritten": rewrite,
        "answer": out["answer"],
        "contexts": contexts,
        "context_hash": store.context_hash(contexts),
        "outcome": out.get("outcome"),
        "refused": is_refusal(out),
        "confidence": out.get("confidence"),
        "sufficiency": out.get("sufficiency"),
        "citation_check": out.get("citation_check"),
        "latency_ms": latency_ms,
        "ts": datetime.now(UTC).isoformat(timespec="seconds"),
    }


def rate(values: list[bool]) -> float:
    return sum(values) / len(values) if values else float("nan")


def summarize(items: list[dict], variants: list[str], fp: str) -> None:
    records = store.load(RESULTS_PATH)
    for variant in variants:
        rows = [(i, records.get(store.key(variant, i["id"], fp))) for i in items]
        rows = [(i, r) for i, r in rows if r and "error" not in r]
        if not rows:
            continue
        latencies = sorted(r["latency_ms"] for _, r in rows)
        answered = [r for _, r in rows if not r["refused"]]
        cc = [r.get("citation_check") or {} for r in answered]

        print(f"\n{variant}: n={len(rows)}")
        print(
            f"  abstention correct : {rate([r['refused'] == (i['expected_outcome'] == 'abstain') for i, r in rows]):.2f}"
        )
        print(
            f"  false-abstain rate : {rate([r['refused'] for i, r in rows if i['expected_outcome'] == 'answer']):.2f}"
        )
        print(
            f"  false-answer rate  : {rate([not r['refused'] for i, r in rows if i['expected_outcome'] == 'abstain']):.2f}"
        )
        print(
            f"  low-confidence     : {rate([r['outcome'] == 'answer_low_confidence' for r in answered]):.2f} of {len(answered)} answered"
        )
        print(
            f"  verifier unparsable: {sum('unparsable' in c.get('reason', '') for c in cc)}, no citations: {sum(c.get('tier') == 'no_citations' for c in cc)}"
        )
        print(
            f"  sufficiency unparsable: {sum('unparsable' in (r.get('sufficiency') or {}).get('reason', '') for _, r in rows)}"
        )
        print(
            f"  latency ms         : p50={latencies[len(latencies) // 2]} max={latencies[-1]}"
        )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--variants", nargs="+", default=["baseline"])
    p.add_argument("--split", choices=["dev", "test", "all"], default="dev")
    p.add_argument(
        "--limit",
        type=int,
        default=0,
        help="max pipeline runs this invocation; 0 = no cap",
    )
    p.add_argument(
        "--gap", type=float, default=30.0, help="minimum seconds per pipeline run"
    )
    p.add_argument(
        "--ci-only",
        action="store_true",
        help="run only items with ci=true, ignoring --split",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    golden = json.loads(DEFAULT_DATASET.read_text(encoding="utf-8"))
    # items = [i for i in golden if args.split == "all" or i["split"] == args.split]
    items = [
        i
        for i in golden
        if (i["ci"] if args.ci_only else args.split in ("all", i["split"]))
    ]
    fp = store.fingerprint()
    done = {
        k
        for k, r in store.load(RESULTS_PATH).items()
        if "error" not in r and r.get("fp") == fp
    }
    pending = [
        (item, variant)
        for item in items
        for variant in args.variants
        if store.key(variant, item["id"], fp) not in done
    ]
    pending = pending[: args.limit] if args.limit else pending
    print(f"fingerprint {fp}: {len(pending)} runs to do, {len(done)} already stored")
    cache = load_rewrites()
    retrieve_context(
        "warm-up"
    )  # retrieval only, no LLM calls; absorbs first-inference cost

    for n, (item, variant) in enumerate(pending, 1):
        started = time.monotonic()
        try:
            rewrite = get_rewrite(item["question"], cache)
            out = run_pipeline(item["question"], rewrite)
        except Exception as e:  # noqa: BLE001
            if (
                isinstance(e, requests.exceptions.HTTPError)
                and e.response.status_code == 429
            ):
                print(
                    "429 persisted after retries; quota likely exhausted. Rerun later to resume."
                )
                break
            record = {
                "key": store.key(variant, item["id"], fp),
                "variant": variant,
                "qid": item["id"],
                "fp": fp,
                "error": str(e),
            }
            store.append(RESULTS_PATH, record)
            print(f"[{n}/{len(pending)}] {variant} {item['id']} ERROR {str(e)[:100]}")
            continue

        latency_ms = int((time.monotonic() - started) * 1000)
        record = to_record(variant, item, fp, rewrite, out, latency_ms)
        store.append(RESULTS_PATH, record)
        print(
            f"[{n}/{len(pending)}] {variant} {item['id']} outcome={record['outcome']} refused={record['refused']} {latency_ms}ms"
        )
        time.sleep(max(0.0, args.gap - (time.monotonic() - started)))
    summarize(items, args.variants, fp)


def _selfcheck() -> None:
    assert is_refusal(
        {"outcome": "abstain", "contexts": ["c"], "answer": "x"}
    )  # nosec B101
    assert is_refusal(
        {
            "outcome": "answer",
            "contexts": ["c"],
            "answer": "I don\u2019t have enough information.",
        }
    )  # nosec B101
    assert not is_refusal(
        {"outcome": "answer", "contexts": ["c"], "answer": "Under the boot floor."}
    )  # nosec B101


if __name__ == "__main__":
    _selfcheck()
    main()
