# Coding Standards

- Prefer readable, focused Python modules and functions.
- Add type hints where they improve clarity and reliability.
- Validate external inputs at system boundaries.
- Handle expected failures explicitly; do not swallow exceptions silently.
- Use structured, appropriately leveled logging.
- Never log secrets or unnecessary sensitive document content.
- Keep provider-specific behavior isolated where practical without adding abstractions without a demonstrated need.
- Add tests for changed behavior and regression fixes.
- Keep configuration out of hard-coded source constants where it varies by environment.
- Document non-obvious decisions and trade-offs.
- Avoid adding dependencies without explaining their value and maintenance cost.
- Run relevant tests and evaluation checks before declaring a change complete.
