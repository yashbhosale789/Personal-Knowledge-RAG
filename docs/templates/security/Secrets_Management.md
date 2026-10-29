# Secrets Management

## Rules
- Never commit secrets or real credential values.
- Use environment variables or a dedicated secret store appropriate to the deployment.
- Keep `.env` and production environment files out of version control.
- Use least-privilege credentials and separate development from production credentials.
- Rotate/revoke credentials promptly after suspected exposure.
- Avoid printing secret values in logs, terminal transcripts, documentation, or chat.

## Environment-variable inventory
Populate this table from the current code/configuration. Do not assume the examples below are all used.

| Variable | Purpose | Required condition | Secret? |
|---|---|---|---|
| `OPENAI_API_KEY` | Provider authentication | If the configured provider requires it | Yes |
| `GROQ_API_KEY` | Provider authentication | If the configured provider requires it | Yes |
| `LANGFUSE_SECRET_KEY` | Tracing authentication | If tracing is enabled | Yes |
| `LANGFUSE_PUBLIC_KEY` | Tracing client identifier | If tracing is enabled | Treat according to provider guidance |
| `LANGFUSE_BASE_URL` | Langfuse region endpoint (must match the project's region) | If tracing is enabled | No |
| `LANGFUSE_TRACING_ENVIRONMENT` | Tags traces by environment (`development` locally, `production` on the prod host); same keys for both | If tracing is enabled | No |
| `DATABASE_URL` | Database connection | If the application uses a database URL | May contain credentials |

## Repository hygiene
- Review tracked environment and Postman files.
- Add appropriate secret-bearing file patterns to `.gitignore`.
- Remember: adding a file to `.gitignore` does not remove it from Git history or untrack an already tracked file.
- If a secret was committed or otherwise exposed, revoke/rotate it; deleting the visible value alone is insufficient.

## GitHub Actions deploy key (F-18, decided 2026-10-29)
GitHub OIDC is not possible on this account: the AWS-managed SCP for projects (Free and Paid plans) denies `iam:*Provider*`, so no OIDC identity provider can be created. Only activating advanced features removes that SCP. The deploy keeps a long-lived access key, hardened instead:

- IAM user `github-deploy` with only `rag-deploy-ssm-only`: `ssm:SendCommand` for the `rag-deploy` document on instance `i-024027af801548268`, plus `ssm:GetCommandInvocation`. The document accepts only a 40-hex commit SHA, so a leaked key can redeploy an existing image and nothing else.
- Stored only as the `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` repo secrets, used only by the `deploy` job.
- **Rotate every 90 days** (last: 2026-10-29, with a rollback drill to 275614f and back to 9473d78, about 75 s per deploy; next: 2027-01-27), and at once on suspected exposure. In bash (prints no secret):
  ```bash
  out=$(aws iam create-access-key --profile yashbhosale789 --user-name github-deploy --query 'AccessKey.[AccessKeyId,SecretAccessKey]' --output text)
  read -r id secret <<<"$out"
  printf %s "$id" | gh secret set AWS_ACCESS_KEY_ID -R yashbhosale789/Personal-Knowledge-RAG
  printf %s "$secret" | gh secret set AWS_SECRET_ACCESS_KEY -R yashbhosale789/Personal-Knowledge-RAG
  ```
  Then re-run the latest `deploy` job (`gh run rerun <run-id> --job <job-id>`), and once it passes, `aws iam delete-access-key` the old key.
- Revisit OIDC if advanced features are ever activated.

## Rotation procedure
1. Identify the credential and systems that use it without copying the value into reports.
2. Revoke or rotate it at the issuing provider.
3. Update the approved secret store/configuration.
4. Redeploy/restart as required.
5. Verify the service works with the replacement.
6. Review logs and repository history for exposure.
