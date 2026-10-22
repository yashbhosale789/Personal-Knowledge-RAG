# Deployment

## Status
Deployment details below are a historical baseline and must be verified against the current infrastructure and repository before execution.

## Previously reported setup
- AWS EC2 t3.small running Ubuntu 26.04.
- Caddy for HTTPS.
- GitHub Actions deployment using AWS Systems Manager (SSM).
- Public endpoint previously reported: `https://yash-pkb-rag.duckdns.org`.
- Warm-up/cache-flush and rollback were previously tested.
- Grafana was optional.

## Before deployment
- Confirm target account, host, domain, configuration, and current deployment workflow.
- Confirm secrets are stored securely and permissions are least-privilege.
- Run required tests and evaluation checks.
- Verify the release revision and rollback target.
- Confirm budget and service quotas.

## Deployment procedure
Populate with exact commands and steps verified from the current workflow and scripts. Never put credential values in this document.

## Post-deployment verification
- Confirm service health and HTTPS.
- Run a safe smoke test.
- Verify logs and metrics.
- Check error rate and resource use.
- Confirm the deployed revision.
- Verify rollback remains possible.
