// Phase 15.4 load test (F-16). Runs locally against prod; never part of the image or CI.
//   $env:BASE_URL = "https://<host>"; $env:API_KEY = "<prod key>"
//   k6 run --summary-export loadtest/r154_summary.json loadtest/query.js
//
// Designed around free-tier quota, not to find a breaking point:
// - Groq gpt-oss-120b: 30 RPM / 8K TPM / 200K TPD; an answered query is ~3 calls, ~2,500 tokens,
//   so ~3 answered queries per minute is the provider ceiling whatever the user count; this runs 2.
// - A Groq 429 on sufficiency/generate makes the app re-run the request on OpenRouter, then Gemini.
//   The run aborts on the first non-Groq, non-200 or verifier_error response, so at most the
//   requests already in flight can spend another provider's quota.
// - Every question is distinct: semantic-cache hits are free and prove nothing (counted, not timed).
import http from "k6/http";
import { check, sleep } from "k6";
import exec from "k6/execution";
import { Counter, Trend } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL;
const API_KEY = __ENV.API_KEY;

// Answerable dev questions, every 5th for a spread across the corpus (12 of 58).
const ANSWERED = JSON.parse(open("../rag-project/eval/data/golden_dataset.json"))
  .filter((i) => i.expected_outcome === "answer" && i.split === "dev" && !i.ci)
  .filter((_, n) => n % 5 === 0)
  .slice(0, 12)
  .map((i) => i.question);

// Off-corpus: rewrite (1 gpt-oss call) + full hybrid retrieval and rerank, then the
// cross-encoder floor abstains without the judge, generator or verifier.
const OFF_CORPUS = [
  "Who painted the ceiling of the Sistine Chapel?",
  "What is the boiling point of water on Mount Everest?",
  "How many moons does Jupiter have?",
  "Who won the 1966 FIFA World Cup?",
  "What is the capital city of Mongolia?",
  "How do you make a classic French omelette?",
  "What year did the Berlin Wall fall?",
  "Which planet has the longest day in the solar system?",
  "Who wrote the novel One Hundred Years of Solitude?",
  "What is the tallest mountain in Africa?",
  "How long does it take light from the Sun to reach Earth?",
  "What is the main ingredient of guacamole?",
  "Which ocean is the deepest?",
  "Who discovered penicillin?",
  "What language is spoken in Brazil?",
  "How many players are on a cricket team?",
  "What is the chemical symbol for tungsten?",
  "Who composed the Four Seasons?",
  "What is the largest desert in Asia?",
  "When did the first person walk on the Moon?",
  "What is the national animal of Scotland?",
  "How many strings does a standard violin have?",
  "Which river flows through Baghdad?",
  "What is the speed of sound in dry air?",
  "Who invented the printing press in Europe?",
  "What is the smallest prime number greater than 50?",
  "Which country hosted the 2016 Summer Olympics?",
  "What is the main gas in Earth's atmosphere?",
  "Who was the first emperor of Rome?",
  "How many bones are in the adult human body?",
];

const quotaErrors = new Counter("quota_or_provider_errors");
const cacheHits = new Counter("cache_hits");
const llmJudged = new Counter("off_corpus_reached_llm_judge");
const serverLatency = new Trend("server_latency_ms", true);

export const options = {
  scenarios: {
    // 10 concurrent users, 3 waves a minute apart: ~10 gpt-oss calls / ~4K tokens per minute.
    off_corpus_10vu: {
      executor: "per-vu-iterations",
      vus: 10,
      iterations: 3,
      maxDuration: "4m",
      exec: "offCorpus",
    },
    // Answered queries under the provider ceiling: 2 per minute (~5K of the 8K TPM) for 6 minutes (12 queries).
    answered_2pm: {
      executor: "constant-arrival-rate",
      rate: 2,
      timeUnit: "1m",
      duration: "6m",
      preAllocatedVUs: 5,
      maxVUs: 5,
      startTime: "4m",
      exec: "answered",
    },
  },
  summaryTrendStats: ["med", "p(95)", "max", "count"],
  thresholds: {
    quota_or_provider_errors: [{ threshold: "count<1", abortOnFail: true }],
    // Non-aborting: they only make the summary report each scenario separately.
    "http_req_duration{scenario:off_corpus_10vu}": ["p(95)<60000"],
    "http_req_duration{scenario:answered_2pm}": ["p(95)<60000"],
    "server_latency_ms{scenario:off_corpus_10vu}": ["p(95)<60000"],
    "server_latency_ms{scenario:answered_2pm}": ["p(95)<60000"],
  },
};

export function setup() {
  if (!BASE_URL || !API_KEY) throw new Error("set BASE_URL and API_KEY");
  if (new Set(ANSWERED).size !== 12) throw new Error("expected 12 distinct answered questions");
}

function ask(query) {
  const res = http.post(
    `${BASE_URL}/query`,
    JSON.stringify({ query, return_contexts: false }),
    {
      headers: { Authorization: `Bearer ${API_KEY}`, "Content-Type": "application/json" },
      timeout: "60s",
    },
  );
  let body = {};
  try {
    body = res.json();
  } catch (_) {}
  const ok = check(res, {
    "status 200": (r) => r.status === 200,
    "answered by groq": () => body.provider === "groq",
    "verifier ran": () => (body.citation_check || {}).tier !== "verifier_error",
  });
  if (!ok) {
    quotaErrors.add(1);
    console.error(`${res.status} provider=${body.provider} outcome=${body.outcome} ${String(res.body).slice(0, 200)}`);
  }
  if (body.outcome === "cached") cacheHits.add(1);
  else if (body.latency_ms !== undefined) serverLatency.add(body.latency_ms);
  return body;
}

export function offCorpus() {
  const started = Date.now();
  const q = OFF_CORPUS[(__VU - 1) * 3 + __ITER];
  const body = ask(q);
  if ((body.sufficiency || {}).tier === "llm_judge") llmJudged.add(1);
  sleep(Math.max(0, 60 - (Date.now() - started) / 1000)); // one wave per minute
}

export function answered() {
  // Each iteration takes the next question; 12 iterations over the run.
  const n = (exec.scenario.iterationInTest || 0) % ANSWERED.length;
  ask(ANSWERED[n]);
}
