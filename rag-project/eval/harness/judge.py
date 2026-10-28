import argparse
import json
import os
import re
import time
from datetime import UTC, datetime
from functools import cache

import numpy as np
import requests

import config
from eval.harness import store
from eval.paths import CALIBRATION_PATH, GEN_PATH, JUDGE_PATH
from eval.paths import GOLDEN_PATH as DEFAULT_DATASET
from src.pipeline.citation_verification import _CITATION_PATTERN
from src.pipeline.confidence import CAVEAT_TEXT
from src.pipeline.json_reply import parse_json_reply

JUDGE_MODEL = "gemini-3.5-flash-lite"
_state = {"last": 0.0, "gap": 4.5}

FAITHFULNESS = """You are evaluating whether an answer is faithful to the given context.

Context:
{context}

Answer: {answer}

Instructions:
1. Break the answer into individual atomic factual claims.
2. For each claim, judge whether it is supported by the context.
3. Return ONLY a JSON object: {{"total": <int>, "supported": <int>}}"""

CORRECTNESS = """You are grading an answer against a reference answer.

Question: {question}
Reference answer: {truth}
Answer to grade: {answer}

Instructions:
1. Split the reference answer into its individual key facts.
2. Count how many key facts the answer to grade states or clearly implies.
3. Say whether the answer to grade contradicts any key fact of the reference.
Return ONLY a JSON object: {{"total": <int>, "covered": <int>, "contradicts": <true or false>}}"""

RELEVANCY = """Given the following answer, write 3 different questions that this answer could be responding to.
Return ONLY a JSON object: {{"questions": ["...", "...", "..."]}}

Answer: {answer}"""


def clean(answer: str) -> str:
    text = _CITATION_PATTERN.sub("", answer.replace(CAVEAT_TEXT, ""))
    return re.sub(r"[ \t\u202f]{2,}", " ", text).strip()


@cache
def embedder():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(config.EMBEDDINGS_MODEL_NAME)


def judge_call(prompt: str) -> str:
    key = os.getenv(config.GEMINI_API_KEY)
    if not key:
        raise ValueError(f"{config.GEMINI_API_KEY} is not set")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {
        "model": JUDGE_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": 2048,
    }

    for attempt in range(4):
        time.sleep(max(0.0, _state["gap"] - (time.monotonic() - _state["last"])))
        try:
            response = requests.post(
                config.GEMINI_API_URL, headers=headers, json=payload, timeout=60
            )
            response.raise_for_status()
            try:
                return (
                    response.json()["choices"][0]["message"]["content"] or ""
                ).strip()
            except (KeyError, IndexError, TypeError):
                return ""
        except (requests.exceptions.Timeout, requests.exceptions.HTTPError) as e:
            status = getattr(e.response, "status_code", None)
            if attempt == 3 or (
                status is not None and status not in {429, 500, 502, 503, 504}
            ):
                raise
            retry_after = (
                e.response.headers.get("retry-after")
                if e.response is not None
                else None
            )
            time.sleep(min(float(retry_after or 5 * 3**attempt), 120))
        finally:
            _state["last"] = time.monotonic()


def faithfulness(question, truth, answer, contexts):
    block = "\n\n".join(f"[C{i}] {c}" for i, c in enumerate(contexts, 1))
    data = parse_json_reply(
        judge_call(FAITHFULNESS.format(context=block, answer=answer))
    )
    total, supported = int(data["total"]), int(data["supported"])
    if total < 1 or not 0 <= supported <= total:
        raise ValueError(f"bad counts: {data}")
    return supported / total, {"total": total, "supported": supported}


def correctness(question, truth, answer, contexts):
    data = parse_json_reply(
        judge_call(CORRECTNESS.format(question=question, truth=truth, answer=answer))
    )
    total, covered = int(data["total"]), int(data["covered"])
    if (
        total < 1
        or not 0 <= covered <= total
        or not isinstance(data["contradicts"], bool)
    ):
        raise ValueError(f"bad verdict: {data}")
    return covered / total, {
        "total": total,
        "covered": covered,
        "contradicts": data["contradicts"],
    }


def relevancy(question, truth, answer, contexts):
    data = parse_json_reply(judge_call(RELEVANCY.format(answer=answer)))
    questions = data["questions"]
    if (
        not isinstance(questions, list)
        or not questions
        or not all(isinstance(q, str) and q.strip() for q in questions)
    ):
        raise ValueError(f"bad questions: {data}")
    vectors = embedder().encode([question] + questions, normalize_embeddings=True)
    return float(np.mean(vectors[1:] @ vectors[0])), {"questions": questions}


METRICS = {
    "faithfulness": faithfulness,
    "correctness": correctness,
    "relevancy": relevancy,
}


def applicable(item: dict) -> list[str]:
    return [
        m for m in METRICS if m != "correctness" or item["expected_outcome"] == "answer"
    ]


def run_metric(
    metric: str, item: dict, answer: str, contexts: list[str]
) -> tuple[float | None, dict]:
    for _ in range(2):
        try:
            score, detail = METRICS[metric](
                item["question"], item["ground_truth"], answer, contexts
            )
            return round(score, 4), detail
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            continue
    return None, {"error": "unparsable"}


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else float("nan")


def auc(good: list[float], bad: list[float]) -> float:
    pairs = [(g, b) for g in good for b in bad]
    if not pairs:
        return float("nan")
    return sum(1.0 if g > b else 0.5 if g == b else 0.0 for g, b in pairs) / len(pairs)


def summarize(variants: list[str], fp: str) -> None:
    rows = [
        r
        for r in store.load(JUDGE_PATH).values()
        if r["fp"] == fp and r["variant"] in variants
    ]
    models = {r["judge_model"] for r in rows}
    if len(models) > 1:
        print("WARNING: mixed judge models:", sorted(models))
    for variant in variants:
        print(f"\n{variant}:")
        for metric in METRICS:
            mine = [
                r for r in rows if r["variant"] == variant and r["metric"] == metric
            ]
            scored = [r["score"] for r in mine if r["score"] is not None]
            extra = ""
            if metric == "correctness":
                extra = f"  contradictions={sum(bool(r['detail'].get('contradicts')) for r in mine if r['score'] is not None)}"
            print(
                f"  {metric:<13} n={len(scored)} failed={len(mine) - len(scored)} mean={mean(scored):.3f}{extra}"
            )


def calibrate() -> None:
    golden = json.loads(DEFAULT_DATASET.read_text(encoding="utf-8"))
    pool = [
        i
        for i in golden
        if i["split"] == "dev" and i["expected_outcome"] == "answer" and i["relevant"]
    ]
    picks = pool[:: max(1, len(pool) // 10)][:10]
    scores = {m: {"good": [], "bad": []} for m in METRICS}
    failed = {m: 0 for m in METRICS}
    for k, item in enumerate(picks):
        others = [
            p
            for p in pool
            if p["relevant"][0]["source"] != item["relevant"][0]["source"]
        ]
        wrong = others[k % len(others)]["ground_truth"]
        contexts = [r["evidence"] for r in item["relevant"]]
        for label, answer in (("good", item["ground_truth"]), ("bad", wrong)):
            for metric in METRICS:
                score, _ = run_metric(metric, item, answer, contexts)
                if score is None:
                    failed[metric] += 1
                else:
                    scores[metric][label].append(score)
        print(f"calibrated {item['id']}")
    report = {}
    for metric, s in scores.items():
        report[metric] = {
            "mean_good": round(mean(s["good"]), 3),
            "mean_bad": round(mean(s["bad"]), 3),
            "auc": round(auc(s["good"], s["bad"]), 3),
            "failed": failed[metric],
        }
        print(f"  {metric:<13} {report[metric]}")
    CALIBRATION_PATH.write_text(
        json.dumps(
            {"judge_model": JUDGE_MODEL, "report": report, "scores": scores}, indent=2
        ),
        encoding="utf-8",
    )

    report = {}
    for metric, s in scores.items():
        report[metric] = {
            "mean_good": round(mean(s["good"]), 3),
            "mean_bad": round(mean(s["bad"]), 3),
            "auc": round(auc(s["good"], s["bad"]), 3),
            "failed": failed[metric],
        }
        print(f"  {metric:<13} {report[metric]}")
    CALIBRATION_PATH.write_text(
        json.dumps(
            {"judge_model": JUDGE_MODEL, "report": report, "scores": scores}, indent=2
        ),
        encoding="utf-8",
    )


def judge_generations(args: argparse.Namespace) -> None:
    golden = {
        i["id"]: i for i in json.loads(DEFAULT_DATASET.read_text(encoding="utf-8"))
    }
    fp = args.fp or store.fingerprint()
    gens = [
        r
        for r in store.load(GEN_PATH).values()
        if r.get("fp") == fp
        and "error" not in r
        and not r["refused"]
        and r["variant"] in args.variants
    ]
    gens.sort(key=lambda r: (int(r["qid"][1:]), r["variant"]))
    done = {k: r for k, r in store.load(JUDGE_PATH).items() if r["score"] is not None}
    pending = [
        (g, m)
        for g in gens
        for m in applicable(golden[g["qid"]])
        if f"{g['key']}|{m}" not in done
    ]
    pending = pending[: args.limit] if args.limit else pending
    print(
        f"fingerprint {fp}: {len(gens)} answered runs, {len(pending)} judgments to do"
    )
    for n, (gen, metric) in enumerate(pending, 1):
        try:
            score, detail = run_metric(
                metric, golden[gen["qid"]], clean(gen["answer"]), gen["contexts"]
            )
        except requests.exceptions.RequestException as e:
            if getattr(e.response, "status_code", None) == 429:
                print(
                    "429 persisted after retries; quota likely exhausted. Rerun later to resume."
                )
                break
            print(f"[{n}/{len(pending)}] {gen['qid']} {metric} ERROR {str(e)[:100]}")
            continue
        record = {
            "key": f"{gen['key']}|{metric}",
            "gen_key": gen["key"],
            "variant": gen["variant"],
            "qid": gen["qid"],
            "fp": gen["fp"],
            "prompt_version": gen.get("prompt_version"),
            "dataset": gen.get("dataset"),
            "corpus": gen.get("corpus"),
            "metric": metric,
            "score": score,
            "detail": detail,
            "judge_model": JUDGE_MODEL,
            "ts": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        store.append(JUDGE_PATH, record)
        print(f"[{n}/{len(pending)}] {gen['variant']} {gen['qid']} {metric} = {score}")
    summarize(args.variants, fp)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--variants", nargs="+", default=["baseline"])
    p.add_argument(
        "--fp", default="", help="generation fingerprint to judge; default = current"
    )
    p.add_argument(
        "--limit",
        type=int,
        default=0,
        help="max judge calls this invocation; 0 = no cap",
    )
    p.add_argument(
        "--gap", type=float, default=4.5, help="minimum seconds between judge calls"
    )
    p.add_argument(
        "--calibrate",
        action="store_true",
        help="run the known-good/bad calibration instead",
    )
    return p.parse_args()


def _selfcheck() -> None:
    assert auc([1.0, 1.0], [0.0, 0.0]) == 1.0 and auc([0.5], [0.5]) == 0.5  # nosec B101
    cleaned = clean("Yes [ SOURCE 2 ]." + CAVEAT_TEXT)
    assert "SOURCE" not in cleaned and "Note" not in cleaned  # nosec B101


def main() -> None:
    args = parse_args()
    _state["gap"] = args.gap
    if args.calibrate:
        calibrate()
    else:
        judge_generations(args)


if __name__ == "__main__":
    _selfcheck()
    main()
