# Incident Response

Use this runbook for suspected credential exposure, unauthorized access, data leakage, compromised dependencies, unexpected cost spikes, or prolonged outages.

## General sequence
1. Detect and record the incident time and observable symptoms.
2. Contain the issue without destroying evidence.
3. Protect affected credentials and data.
4. Investigate scope using approved logs and configuration; do not copy secrets into reports.
5. Recover using a known-good configuration or deployment.
6. Verify service health and security controls.
7. Record root cause, impact, remediation, and prevention actions.

## Credential exposure
- Revoke/rotate the exposed credential immediately.
- Identify affected services and update their configuration.
- Review repository history and CI logs.
- Verify old credentials no longer work.
- Do not treat deleting the latest file copy as sufficient remediation.

## Data exposure
- Restrict the affected endpoint, dataset, or access path as appropriate.
- Preserve relevant evidence with access controls.
- Determine which data may have been accessed.
- Correct authorization/retrieval controls and test them.
- Follow applicable notification obligations based on the actual circumstances.

## Outage or unexpected cost
- Check recent deployments, provider status, request volume, error rates, quotas, and resource use.
- Apply safe traffic/feature limits where necessary.
- Roll back if a recent change is implicated.
- Verify recovery and document the cause.

## After-action record
Date/time; severity; impact; timeline; root cause; containment; recovery; verification; follow-up tasks; owner.
