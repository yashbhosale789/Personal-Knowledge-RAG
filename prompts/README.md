# Developer & AI Assistant Prompt Workflows

This directory contains reusable prompt templates and operational workflows for collaborating with AI assistants (Claude, Gemini, ChatGPT, local LLMs) on this repository.

These files are developer workflow instructions, not application code or production documentation.

## Workflow Prompts

| Workflow Prompt | Purpose | When to Use |
| :--- | :--- | :--- |
| [`session-startup.md`](file:///D:/Development/GenAI/Personal%20Knowledge%20OS%20(RAG%20System)/prompts/workflows/session-startup.md) | Session-start context retrieval checklist | Run at the start of a new working session to align the assistant on project status, roadmap phase, and pending tasks. |
| [`session-memory-update.md`](file:///D:/Development/GenAI/Personal%20Knowledge%20OS%20(RAG%20System)/prompts/workflows/session-memory-update.md) | End-of-session state & memory capture | Run at the end of a session to summarize decisions, bug fixes, test results, and next actions. |
| [`production-readiness-review.md`](file:///D:/Development/GenAI/Personal%20Knowledge%20OS%20(RAG%20System)/prompts/workflows/production-readiness-review.md) | Skeptical architectural and security review | Run before deploying or cutting releases to audit trust boundaries, validation, telemetry, and error handling. |
| [`documentation-setup.md`](file:///D:/Development/GenAI/Personal%20Knowledge%20OS%20(RAG%20System)/prompts/workflows/documentation-setup.md) | Staged documentation audit and scaffolding | Run when establishing or auditing repository documentation standards. |
| [`documentation-maintenance.md`](file:///D:/Development/GenAI/Personal%20Knowledge%20OS%20(RAG%20System)/prompts/workflows/documentation-maintenance.md) | Drift detection and documentation audit | Run periodically to ensure markdown documentation accurately matches codebase reality. |

## Usage Guidelines
- **Context Grounding:** Pair these prompts with [`docs/architecture/system-context.md`](file:///D:/Development/GenAI/Personal%20Knowledge%20OS%20(RAG%20System)/docs/architecture/system-context.md) and [`docs/architecture/roadmap.md`](file:///D:/Development/GenAI/Personal%20Knowledge%20OS%20(RAG%20System)/docs/architecture/roadmap.md) to keep AI context accurate.
- **Evidence-Based:** Always demand that the assistant inspect the source code in `rag-project/` rather than hallucinating implementation details.
