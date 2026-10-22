# Dependency Management

## Source of truth
The repository's actual dependency and lock files are authoritative. Record the Python version and installation commands only after verifying them.

## Policy
- Pin or constrain versions consistently with the project's dependency manager.
- Use a reproducible environment for CI and deployment.
- Review release notes and compatibility before upgrading core RAG/LLM libraries.
- Run tests and the evaluation baseline after meaningful upgrades.
- Audit known vulnerabilities.
- Remove unused dependencies.
- Avoid upgrading multiple major components at once unless necessary.

## Upgrade record
For significant upgrades, record package/version changes, reason, compatibility issues, test results, evaluation impact, and rollback approach.
