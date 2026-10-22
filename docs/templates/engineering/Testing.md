# Testing Strategy

## Test layers
- Unit tests for deterministic functions and validation.
- Integration tests for ingestion, vector-store behavior, retrieval, and provider adapters.
- API tests for request/response contracts and failure paths.
- Security tests for upload constraints, authorization boundaries, and prompt-injection handling.
- Regression tests for previously fixed bugs.
- Evaluation tests for retrieval and generated-answer quality.

## Commands
Populate this section with commands verified in the current repository:
- Unit tests:
- Integration tests:
- Lint/type checks:
- Evaluation validation:
- Full evaluation:

## Pull-request expectations
- Add or update tests for changed behavior.
- Run relevant tests and report actual results.
- Explain tests not run and why.
- Avoid tests that require paid services unless explicitly approved; provide a deterministic or mocked path where appropriate.

## Completion criteria
A test suite passing does not automatically prove RAG quality, security, or production readiness. Record what each test covers and what remains untested.
