# Security

## Purpose
Describe the security controls actually implemented by this application. This document is a template until each control is verified against source code, configuration, and deployment settings.

## Security objectives
- Protect credentials and sensitive documents.
- Restrict access to data and operations according to the application's authorization model.
- Treat user input and retrieved document content as untrusted.
- Bound resource consumption and external-provider costs.
- Avoid exposing sensitive content through logs, traces, errors, or evaluation artifacts.

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
