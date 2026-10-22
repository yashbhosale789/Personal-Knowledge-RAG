# Prompt — Documentation Setup

Audit and improve this repository's documentation without overengineering it.

## Core context
The project has separate context files: `Ponytail.md`, `Roadmap.md`, `Architecture.md`, and `Memory.md`. Treat repository implementation as the source of truth for what is currently implemented, the roadmap as the intended sequence, and memory as historical context.

## Process
1. Audit existing Markdown files and repository structure.
2. Inspect code, tests, configuration, evaluation artifacts, CI/CD, and deployment scripts relevant to each claim.
3. Propose a file map and identify duplication before writing.
4. Create/update documentation in small groups, after the user approves the plan.
5. Validate links, paths, consistency, and factual claims.

## Suggested documentation areas
- Core: README, CONTRIBUTING, CHANGELOG.
- Security: security policy, threat model, secrets, privacy, incident response.
- Engineering: testing, RAG evaluation, observability, performance, error handling, dependencies.
- Operations: deployment, CI/CD, rollback, backup/recovery, runbooks, cost.
- Development: API, configuration, local setup, coding standards, vector store.

Do not create every suggested file automatically. Create a file only when it serves a clear purpose and has evidence-supported content. Avoid duplicating architecture, roadmap, and memory. Never include secret values. Label controls and features as implemented, unverified, planned, recommended, or unknown.

Start with an audit and proposed plan only. Do not create or modify files until the user approves.
