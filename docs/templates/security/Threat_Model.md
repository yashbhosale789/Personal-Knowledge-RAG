# Threat Model

## Scope
The RAG application, document-ingestion path, vector store, API/UI, model/embedding providers, logs/traces, deployment pipeline, and credentials.

## Assets
- User documents and extracted text.
- Embeddings and vector-store metadata.
- Prompts, queries, and generated answers.
- Provider credentials and deployment credentials.
- Evaluation datasets, traces, logs, and backups.
- Availability and provider/infrastructure budget.

## Trust boundaries
- User/browser to application API.
- Uploaded files to parsers.
- Retrieved document text to the model.
- Application to external model/embedding/tracing providers.
- CI/CD to cloud infrastructure.
- Application to logs, metrics, traces, and backups.

## Threats to assess
| Threat | Potential impact | Controls to verify |
|---|---|---|
| Direct/indirect prompt injection | Unsafe instructions influence generation or tools | Treat retrieved text as untrusted; adversarial tests; restrict tool authority |
| Unauthorized retrieval | Data from another user's collection is returned | Enforce authorization in retrieval/data layer |
| Malicious/oversized document | Parser compromise or resource exhaustion | File allowlist, size limits, timeouts, isolation where appropriate |
| Secret leakage | Account or service compromise | Secret scanning, safe config, rotation and revocation |
| API/provider abuse | Excess cost or service outage | Rate limits, quotas, timeouts, concurrency bounds |
| Sensitive trace/log content | Confidentiality breach | Redaction, access control, retention limits |
| Dependency compromise | Code execution or data exposure | Dependency auditing, pinning, controlled updates |
| CI/CD credential abuse | Unauthorized deployment | Least privilege, protected secrets, workflow review |

## Assessment format
For each finding record evidence, likelihood, impact, severity, existing controls, gaps, owner, remediation, and verification. Mark controls as verified only after inspecting implementation/configuration or running an appropriate test.
