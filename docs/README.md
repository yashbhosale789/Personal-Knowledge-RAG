# Personal Knowledge OS — Documentation Hub

Welcome to the documentation hub for **Personal Knowledge OS (RAG System)**. This directory contains architectural specifications, operational runbooks, engineering templates, and project history.

---

## Navigation & Directory Map

```text
docs/
├── architecture/         # System design, architectural targets, and multi-phase roadmap
│   ├── system-context.md # Target architecture, RAG quality metrics, production engineering rules
│   └── roadmap.md        # Comprehensive 21-phase roadmap (Current status: Phase 11)
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

## Core Reading

1. **System Context & Principles:**  
   Read [`docs/architecture/system-context.md`](file:///D:/Development/GenAI/Personal%20Knowledge%20OS%20(RAG%20System)/docs/architecture/system-context.md) for the core target architecture:
   ```text
   User → AuthN/AuthZ → Query Understanding → Hybrid Retrieval (Vector + BM25)
        → Reranking → Context Sufficiency → Grounded LLM → Citation Verification
        → Confidence Scoring → Logging + Metrics + Evaluation
   ```

2. **Project Roadmap:**  
   Read [`docs/architecture/roadmap.md`](file:///D:/Development/GenAI/Personal%20Knowledge%20OS%20(RAG%20System)/docs/architecture/roadmap.md) to track milestones across Phases 1–21 (Phase 1–10 completed, currently in Phase 11 Pre-Deployment Hardening).

3. **Operations Runbook:**  
   Read [`docs/runbooks/redis-stack-guide.md`](file:///D:/Development/GenAI/Personal%20Knowledge%20OS%20(RAG%20System)/docs/runbooks/redis-stack-guide.md) for Redis Stack container management, semantic cache inspection, and RediSearch index commands.

---

## Related Repositories & Tooling

- **Core Codebase:** The active production RAG application lives in [`rag-project/`](file:///D:/Development/GenAI/Personal%20Knowledge%20OS%20(RAG%20System)/rag-project).
- **Prompt Engineering & Workflows:** Assistant and collaboration workflows live in [`prompts/`](file:///D:/Development/GenAI/Personal%20Knowledge%20OS%20(RAG%20System)/prompts).
- **Deployment Automation:** EC2 SSM deployment scripts live in [`deploy/`](file:///D:/Development/GenAI/Personal%20Knowledge%20OS%20(RAG%20System)/deploy).
- **API Testing:** Postman collections and environments live in [`postman/`](file:///D:/Development/GenAI/Personal%20Knowledge%20OS%20(RAG%20System)/postman).
