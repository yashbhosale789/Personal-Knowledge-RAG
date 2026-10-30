import type { QueryResponse } from "./api";

export const REQUEST_ID = "6f1c2a9e-3b4d-4e5f-8a9b-0c1d2e3f4a5b";

export const answer = (overrides: Partial<QueryResponse> = {}): QueryResponse => ({
  query_id: REQUEST_ID,
  answer: "Loosen the lug nuts before jacking the car [SOURCE 1].",
  latency_ms: 3210,
  outcome: "answer",
  confidence: "high",
  sufficiency: { sufficient: true, reason: "Context covers it.", tier: "llm_judge" },
  citation_check: { grounded: true, unsupported_claims: [], reason: "All supported.", tier: "llm_judge" },
  chunks: [
    { n: 1, source: "aventro_manual.pdf", page: "12", snippet: "Loosen each lug nut half a turn.", cited: true },
    { n: 2, source: "warranty.pdf", page: null, snippet: "Tyres are not covered.", cited: false },
  ],
  ...overrides,
});

/** A /query/stream body: tokens, then the final event (or an error event instead). */
export function sse(tokens: string[], last: { final: QueryResponse } | { error: { status: number; error: string } }): string {
  const events = tokens.map((text) => ["token", { text }] as const);
  const [name, data] = "final" in last ? ["final", last.final] : ["error", last.error];
  return [...events, [name, data] as const].map(([e, d]) => `event: ${e}\ndata: ${JSON.stringify(d)}\n\n`).join("");
}
