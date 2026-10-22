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
| `DATABASE_URL` | Database connection | If the application uses a database URL | May contain credentials |

## Repository hygiene
- Review tracked environment and Postman files.
- Add appropriate secret-bearing file patterns to `.gitignore`.
- Remember: adding a file to `.gitignore` does not remove it from Git history or untrack an already tracked file.
- If a secret was committed or otherwise exposed, revoke/rotate it; deleting the visible value alone is insufficient.

## Rotation procedure
1. Identify the credential and systems that use it without copying the value into reports.
2. Revoke or rotate it at the issuing provider.
3. Update the approved secret store/configuration.
4. Redeploy/restart as required.
5. Verify the service works with the replacement.
6. Review logs and repository history for exposure.
