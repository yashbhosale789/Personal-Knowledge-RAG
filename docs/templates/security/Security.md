# Security

## Purpose
Describe the security controls actually implemented by this application. This document is a template until each control is verified against source code, configuration, and deployment settings.

## Security objectives
- Protect credentials and sensitive documents.
- Restrict access to data and operations according to the application's authorization model.
- Treat user input and retrieved document content as untrusted.
- Bound resource consumption and external-provider costs.
- Avoid exposing sensitive content through logs, traces, errors, or evaluation artifacts.

## Authorization model (decided 2026-10-29, Phase 13.5)
Single-user system with one shared API key. This is a deliberate decision, not a gap.

- Every endpoint except `/health` and `/metrics` requires `Authorization: Bearer <API_KEY>` (`api/core/auth.py`). The comparison is constant-time and fails closed (401) when `API_KEY` is unset. In prod, Caddy also blocks `/metrics` and `/ingest` from the internet, so only `/query` and `/health` are public.
- Every key holder sees every document: there is no per-user identity, no document-level access control, and one shared semantic cache. Rate limits are keyed on the key's SHA-256 hash.
- The key is the only boundary, so anyone holding it holds the whole corpus. Rotate it in the server `.env` (and restart `app`) if it may have leaked.
- Revisit if a second user is ever added: that needs per-user keys, a per-user cache namespace and document filtering at retrieval time, all decided before the second user gets access.

## Controls to verify
- [ ] Authentication and authorization requirements are documented.
- [ ] Request schemas and inputs are validated.
- [ ] File types, file sizes, and parser resource limits are enforced.
- [ ] API rate limits, timeouts, and concurrency limits are considered.
- [ ] Retrieved content is treated as untrusted data, not trusted instructions.
- [ ] Document access controls are enforced before returning retrieved content, if multi-user permissions apply.
- [ ] Secrets are supplied through approved configuration/secret mechanisms.
- [ ] Logs and traces redact secrets and unnecessary sensitive content.
- [ ] Dependencies and deployment permissions are reviewed.
- [ ] Backup, deletion, and incident procedures are documented.

## Known/open issues
Record verified findings with owner, severity, remediation, and verification evidence. A previously reported concern involved potentially credential-bearing files under `postman/environments`; inspect the current repository and resolve it before marking closed.

## Reporting
Document the private vulnerability-reporting channel appropriate to the project before publishing this file. Do not publish exploit details or credentials in public issue trackers.
