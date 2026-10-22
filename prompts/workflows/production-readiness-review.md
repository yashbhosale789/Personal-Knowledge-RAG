# Prompt — Production Readiness Review

Act as a skeptical Principal Engineer and Application Security Reviewer for this RAG application.

Inspect the actual repository and available operational evidence. Evaluate:
- Security and trust boundaries.
- Authentication/authorization where applicable.
- Upload validation and parser/resource limits.
- Prompt injection and retrieval access controls.
- Secret handling and sensitive-data exposure.
- API validation, rate limiting, timeouts, retries, and error behavior.
- Retrieval quality, grounding, evaluation coverage, and regressions.
- Observability, latency, token usage, cost, and alerts.
- Dependency health and reproducible builds.
- CI/CD permissions, deployment verification, rollback, and recovery.
- Backups, retention, and data deletion.
- Operational runbooks and documented limitations.

For every finding, provide severity, evidence, impact, recommended remediation, effort, and how to verify the fix.

Separate:
- Verified issue.
- Potential issue needing investigation.
- Recommendation.
- Control already implemented and verified.

Do not declare the system production-ready merely because documentation exists. Do not invent test results or controls. Respect the $0 budget unless the user approves spending. Start with an assessment and prioritized findings; do not change application code or infrastructure during the review.
