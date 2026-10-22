# Personal Knowledge OS — Documentation Hub

Welcome to the documentation hub for **Personal Knowledge OS (RAG System)**. This directory contains architectural specifications, operational runbooks, engineering templates, and project history.

---

## Navigation & Directory Map

```text
docs/
├── context/              # Core AI Project Context Files (Claude Context / System Grounding)
│   ├── Architecture.md   # System goals, grounding principles, security, and production DoD
│   ├── Roadmap.md        # Detailed phase plan (Phases 1–12 closed, Phase 13 active)
│   ├── Memory.md         # Consolidated persistent memory across sessions & verified facts
│   └── Ponytail.md       # Senior lazy developer discipline (YAGNI, root cause, shortest diff)
├── architecture/         # System design, architectural targets, and multi-phase roadmap
│   ├── system-context.md # Target architecture, RAG quality metrics, production engineering rules
│   └── roadmap.md        # Comprehensive 21-phase roadmap (Current status: Phase 13)
├── runbooks/             # Operational procedures, infrastructure setup, and troubleshooting
│   └── redis-stack-guide.md # Redis Stack, RediSearch CLI commands, rate limiting & cache lifecycle
├── templates/            # Engineering specifications & runbook scaffolding templates
│   ├── development/      # API, Coding Standards, Configuration, Vector Store, Local Dev
│   ├── engineering/      # Evaluation, Testing, Observability, Performance, Error Handling
│   ├── operations/       # Deployment, Rollback, CI/CD, Backup/Recovery, Runbook, Cost
│   └── security/         # Threat Model, Security Posture, Secrets, Privacy, Incident Response
└── archive/              # Historical milestone reports and learning journals
    ├── Phase1_Naive_RAG_Report.docx
    ├── Phase1_RAG_Report.docx
    ├── Phase2_Advanced_RAG_Report.docx
    ├── Phase3_RAG_Evaluation_Report.docx
    ├── Phase4_Agentic_RAG_Report.docx
    ├── RAG_Learning_Journal.docx
    └── rag_learning_prompts_project1.docx
```

---

## Core Reading & AI Context

1. **AI Project Context Files:**
   - [`docs/context/Architecture.md`](file:///D:/Development/GenAI/Personal%20Knowledge%20OS%20(RAG%20System)/docs/context/Architecture.md): System architecture principles, grounding rules, and production definition of done.
   - [`docs/context/Roadmap.md`](file:///D:/Development/GenAI/Personal%20Knowledge%20OS%20(RAG%20System)/docs/context/Roadmap.md): Master roadmap from Phase 1 through Phase 21 (Phases 1–12 closed; Phase 13 active).
   - [`docs/context/Memory.md`](file:///D:/Development/GenAI/Personal%20Knowledge%20OS%20(RAG%20System)/docs/context/Memory.md): Consolidated durable memory across sessions, verified facts, decisions, and constraints.
   - [`docs/context/Ponytail.md`](file:///D:/Development/GenAI/Personal%20Knowledge%20OS%20(RAG%20System)/docs/context/Ponytail.md): Senior lazy developer discipline (YAGNI, root cause over symptom, shortest working diff).

2. **System Context & Principles:**  
   Read [`docs/architecture/system-context.md`](file:///D:/Development/GenAI/Personal%20Knowledge%20OS%20(RAG%20System)/docs/architecture/system-context.md) for the core target architecture:
   ```text
   User → AuthN/AuthZ → Query Understanding → Hybrid Retrieval (Vector + BM25)
        → Reranking → Context Sufficiency → Grounded LLM → Citation Verification
        → Confidence Scoring → Logging + Metrics + Evaluation
   ```

3. **Project Roadmap:**  
   Read [`docs/architecture/roadmap.md`](file:///D:/Development/GenAI/Personal%20Knowledge%20OS%20(RAG%20System)/docs/architecture/roadmap.md) to track milestones across Phases 1–21 (Phases 1–12 completed, deployed to AWS; currently active on Phase 13 LLMOps).

4. **Operations Runbook:**  
   Read [`docs/runbooks/redis-stack-guide.md`](file:///D:/Development/GenAI/Personal%20Knowledge%20OS%20(RAG%20System)/docs/runbooks/redis-stack-guide.md) for Redis Stack container management, semantic cache inspection, and RediSearch index commands.

---

## Related Repositories & Tooling

- **Core Codebase:** The active production RAG application lives in [`rag-project/`](file:///D:/Development/GenAI/Personal%20Knowledge%20OS%20(RAG%20System)/rag-project).
- **Prompt Engineering & Workflows:** Assistant and collaboration workflows live in [`prompts/`](file:///D:/Development/GenAI/Personal%20Knowledge%20OS%20(RAG%20System)/prompts).
- **Deployment Automation:** EC2 SSM deployment scripts live in [`deploy/`](file:///D:/Development/GenAI/Personal%20Knowledge%20OS%20(RAG%20System)/deploy).
- **API Testing:** Postman collections and environments live in [`postman/`](file:///D:/Development/GenAI/Personal%20Knowledge%20OS%20(RAG%20System)/postman).
