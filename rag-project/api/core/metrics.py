from prometheus_client import Counter, Histogram, Info

from config import PROMPT_VERSION

PROVIDER_LATENCY_BUCKETS = (0.1, 0.25, 0.5, 1, 2, 5, 10, 20, 30)

http_requests_total = Counter(
    "http_requests_total", "Total HTTP Requests", ["method", "path", "status_code"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP requests latency in seconds",
    ["method", "path"],
)

provider_call_duration_seconds = Histogram(
    "provider_call_duration_seconds",
    "Latency of a single successful provider call attempt",
    ["provider"],
    buckets=PROVIDER_LATENCY_BUCKETS,
)

provider_call_errors_total = Counter(
    "provider_call_errors_total", "Total failed provider call attempt.", ["provider"]
)

provider_retries_total = Counter(
    "provider_retries_total",
    "Total retries issued after a failed provider attempt.",
    ["provider"],
)

provider_requests_total = Counter(
    "provider_requests_total",
    "Total logical requests per provider, by final outcome.",
    ["provider", "outcome"],
)

rag_query_outcomes_total = Counter(
    "rag_query_outcomes_total",
    "Served /query requests by outcome: cached | answer | answer_low_confidence "
    "(citation check failed) | abstain (insufficient context) | empty (nothing retrieved).",
    ["outcome"],
)

# Constant per deploy: rag_prompt_info{version="..."} 1
prompt_info = Info("rag_prompt", "Pipeline prompt version in use.")
prompt_info.info({"version": PROMPT_VERSION})
