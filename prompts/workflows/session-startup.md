# Prompt — Session Startup

Use at the beginning of a substantial new chat if the project context files have not already been retrieved.

Read the available project context files (located in `docs/context/` or uploaded to Claude Project Context):
1. `docs/context/Ponytail.md` (or `Ponytail.md`)
2. `docs/context/Roadmap.md` (or `Roadmap.md`)
3. `docs/context/Architecture.md` (or `Architecture.md`)
4. `docs/context/Memory.md` (or `Memory.md`)

Then retrieve only the repository documentation relevant to the task.

Establish:
- Current phase/subphase and next agreed task.
- Relevant decisions and rejected alternatives.
- Constraints, acceptance criteria, and unresolved risks.
- Which implementation details require repository verification.

Do not claim to have read inaccessible files. Do not assume remembered implementation facts are current. If the task depends on code, inspect the relevant source, tests, configuration, and workflows before recommending a change.

Respond with a concise continuity summary only when useful; do not dump the entire project history.
