// Mirrors the fields of api/models/responses.py QueryResponse that the UI reads.
export interface QueryResponse {
  query_id: string;
  answer: string;
  sources: string[];
  latency_ms: number;
  outcome: string | null;
  confidence: string | null;
  sufficiency: { sufficient: boolean; reason: string; tier: string } | null;
  citation_check: { grounded: boolean; unsupported_claims: string[]; reason: string; tier: string } | null;
}

export type Rating = "up" | "down";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

const MESSAGES: Record<number, string> = {
  401: "The API key was rejected. Enter it again.",
  429: "Rate limit reached. Wait a minute and try again.",
  502: "Every LLM provider failed. Try again shortly.",
  503: "The service is starting or unavailable. Try again shortly.",
};

async function post<T>(path: string, apiKey: string, body: object): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
      body: JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "Network error: the server could not be reached.");
  }
  if (!res.ok) throw new ApiError(res.status, MESSAGES[res.status] ?? `Request failed (${res.status}).`);
  return res.json() as Promise<T>;
}

export const postQuery = (apiKey: string, query: string) => post<QueryResponse>("/query", apiKey, { query });

export const postFeedback = (apiKey: string, requestId: string, rating: Rating, comment: string) =>
  // An empty comment is omitted: the API stores it as no comment.
  post<{ status: string }>("/feedback", apiKey, { request_id: requestId, rating, comment: comment || undefined });
