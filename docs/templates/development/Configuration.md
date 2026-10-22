# Configuration

## Rules
Document only configuration variables verified in code, deployment files, or environment examples. Never include real secret values.

For each setting record:
- Name.
- Purpose.
- Required/optional condition.
- Default, if one actually exists.
- Accepted values.
- Which environment uses it.
- Whether it contains a secret.

## Environment separation
Document development, testing, and production configuration separately. Keep secret-bearing local files out of version control and explain how to create a safe local configuration.
