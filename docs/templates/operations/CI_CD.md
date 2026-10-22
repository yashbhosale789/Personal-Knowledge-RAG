# CI/CD

## Document the actual workflow
Record workflow files, trigger paths, branch rules, permissions, test stages, deployment mechanism, and post-deploy verification after inspecting the repository.

## Previously reported behavior to verify
- GitHub Actions deployed through AWS SSM.
- Deployment used IAM user access keys because OIDC was unavailable in the user's then-current setup.
- README-only changes did not trigger deployment.

These are historical notes, not guaranteed current configuration.

## Security checklist
- Use least-privilege permissions.
- Restrict secrets to required workflows/environments.
- Avoid printing secrets.
- Pin third-party actions according to project policy.
- Protect deployment branches and environments where available.
- Audit workflow trigger filters.
- Rotate/revoke exposed credentials.
- Verify the deployed commit and smoke-test result.

## Recovery
Link to `Rollback.md` and document how a failed deployment is detected and handled.
