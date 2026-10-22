# Prompt — Documentation Maintenance

Audit the project's Markdown documentation against the current repository.

First inspect `Ponytail.md`, `Roadmap.md`, `Architecture.md`, `Memory.md`, the README, and relevant documentation. Then inspect source code, tests, configuration, CI/CD workflows, deployment scripts, and evaluation artifacts as needed.

Report:
- Outdated or contradicted claims.
- Missing documentation for implemented behavior.
- Planned work incorrectly described as implemented.
- Duplicate or conflicting descriptions.
- Broken internal links and incorrect file paths.
- Potentially exposed secrets (identify file paths, never print secret values).
- Documentation that can be deleted or merged safely.

Do not modify application code. Do not delete documentation. Propose a minimal update plan first. After approval, update only the relevant files and validate links, consistency, and claims against available evidence.
