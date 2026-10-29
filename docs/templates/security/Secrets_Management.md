# Secrets Management

## Rules
- Never commit secrets or real credential values.
- Use environment variables or a dedicated secret store appropriate to the deployment.
- Keep `.env` and production environment files out of version control.
- Use least-privilege credentials and separate development from production credentials.
- Rotate/revoke credentials promptly after suspected exposure.
- Avoid printing secret values in logs, terminal transcripts, documentation, or chat.

## Environment-variable inventory
The full list, with what each variable does and which ones only the prod server needs, is `rag-project/.env.sample` (placeholders only). Copy it to `rag-project/.env` and fill it in; keep that file and the sample in sync when a variable is added or removed.

Where to get each secret (all free tiers):

| Variable | Where to create it |
|---|---|
| `GROQ_API_KEY` | https://console.groq.com/keys |
| `OPENROUTER_API_KEY` | https://openrouter.ai/settings/keys |
| `GEMINI_API_KEY` | https://aistudio.google.com/apikey |
| `HF_TOKEN` (optional, read access is enough) | https://huggingface.co/settings/tokens |
| `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` (optional) | https://cloud.langfuse.com → project → Settings → API Keys |
| `GF_SMTP_PASSWORD` (prod only) | https://myaccount.google.com/apppasswords (needs 2-Step Verification) |
| `API_KEY`, `GRAFANA_ADMIN_PASSWORD` | Generate locally: `python -c "import secrets; print(secrets.token_urlsafe(32))"` |

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
