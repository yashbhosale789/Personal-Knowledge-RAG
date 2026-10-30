import type { QueryResponse } from "./api";

export const REQUEST_ID = "6f1c2a9e-3b4d-4e5f-8a9b-0c1d2e3f4a5b";

export const answer = (overrides: Partial<QueryResponse> = {}): QueryResponse => ({
  query_id: REQUEST_ID,
  answer: "Loosen the lug nuts before jacking the car [SOURCE 1].",
  sources: ["aventro_manual.pdf"],
  latency_ms: 3210,
  outcome: "answer",
  confidence: "high",
  sufficiency: { sufficient: true, reason: "Context covers it.", tier: "llm_judge" },
  citation_check: { grounded: true, unsupported_claims: [], reason: "All supported.", tier: "llm_judge" },
  ...overrides,
});
