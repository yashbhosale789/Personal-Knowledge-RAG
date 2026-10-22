# Error Handling

Document the actual application behavior for:
- Invalid requests.
- Unsupported or malformed files.
- Parsing failures.
- Empty or low-confidence retrieval.
- Embedding/vector-store failures.
- LLM provider errors and rate limits.
- Timeouts and retries.
- Invalid model output.
- Observability failures.

## Principles
- Return safe, actionable errors without secrets or internal stack traces to public clients.
- Log enough diagnostic context without logging sensitive content.
- Bound retries and use backoff where appropriate.
- Avoid retrying non-recoverable errors.
- Do not silently substitute a different model/provider unless that behavior is explicitly configured and observable.
- When evidence is insufficient, the RAG response should communicate that limitation rather than fabricate a grounded answer.

Populate endpoint-specific status codes and response examples from the implementation.
