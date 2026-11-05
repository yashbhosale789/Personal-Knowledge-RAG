# Security Policy

## Supported versions

Only the latest commit on `main`, which is what runs at [yash-pkb-rag.duckdns.org](https://yash-pkb-rag.duckdns.org), receives fixes. There are no versioned releases.

## Reporting a vulnerability

Please report privately through GitHub: **[Report a vulnerability](https://github.com/yashbhosale789/Personal-Knowledge-RAG/security/advisories/new)** (Security tab → Advisories). Do not open a public issue for a suspected vulnerability, and never paste a credential into an issue, PR or chat, even an exposed one.

Include what you found, how to reproduce it, and the impact you expect. This is a personal project with one maintainer, so responses are best effort; confirmed issues are fixed on `main` and noted in the [changelog](CHANGELOG.md).

**In scope:** the API and UI in `rag-project/`, the deployment configuration (Caddy, Compose, `deploy.sh`, workflows), and prompt-injection paths through ingested documents, chat history or feedback.

**Out of scope:** the free-tier rate limits of the LLM providers, denial of service by volume, and findings that need the shared API key (it grants full access by design: this is a single-user system).

## How the system is protected

- **Access:** a bearer key on every endpoint except `/health` and `/metrics`; it fails closed and must be at least 16 characters. Redis rate limits per key. `/metrics` and `/ingest` are not reachable from the internet.
- **Untrusted input:** document text, chat history and feedback comments are treated as data, never as instructions. Ingested documents pass a prompt-injection scanner; uploads are checked for name, `%PDF-` header, size and extracted length.
- **Front end:** plain-text rendering, and a Content-Security-Policy that allows only same-origin scripts and requests. The key is kept in `sessionStorage` only.
- **Transport and host:** HTTPS through Caddy; no SSH port (deploys run through AWS Systems Manager); least-privilege deploy key rotated every 90 days.
- **Supply chain:** `bandit` and `ruff` as hard gates, `pip-audit`, Dependabot and CodeQL in CI; pinned lock files and a pinned Redis image digest.
- **Data:** Langfuse traces mask content by default; feedback text is deleted after 90 days.

One incident (keys committed, 2026-10-29) is written up in the [roadmap](docs/architecture/roadmap.md) with its fixes. Further detail: [threat model](docs/templates/security/Threat_Model.md), [security posture](docs/templates/security/Security.md), [secrets management](docs/templates/security/Secrets_Management.md), [data privacy](docs/templates/security/Data_Privacy.md), [incident response](docs/templates/security/Incident_Response.md).
