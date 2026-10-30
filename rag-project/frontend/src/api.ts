export interface Chunk {
  n: number;
  source: string;
  page: string | number | null;
  snippet: string;
  cited: boolean;
}

// The `final` event of POST /query/stream (api/models/responses.py QueryStreamFinal); only the fields the UI reads.
export interface QueryResponse {
  query_id: string;
  answer: string;
  latency_ms: number;
  outcome: string | null;
  confidence: string | null;
  sufficiency: { sufficient: boolean; reason: string; tier: string } | null;
  citation_check: { grounded: boolean; unsupported_claims: string[]; reason: string; tier: string } | null;
  chunks: Chunk[];
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

async function post(path: string, apiKey: string, body: object): Promise<Response> {
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
  return res;
}

/** Streams the answer to onToken as it is generated; resolves with the `final` event. */
export async function streamQuery(apiKey: string, query: string, onToken: (text: string) => void): Promise<QueryResponse> {
  const res = await post("/query/stream", apiKey, { query });
  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    // Events are "event: <name>\ndata: <json>\n\n"; the JSON never contains a raw newline.
    let end;
    while ((end = buffer.indexOf("\n\n")) >= 0) {
      const block = buffer.slice(0, end);
      buffer = buffer.slice(end + 2);
      const event = /^event: (.*)$/m.exec(block)?.[1];
      const data = JSON.parse(/^data: (.*)$/m.exec(block)?.[1] ?? "null");
      if (event === "token") onToken(data.text);
      else if (event === "final") return data as QueryResponse;
      else if (event === "error") throw new ApiError(data.status, data.error);
    }
  }
  throw new ApiError(0, "The answer stream ended early. Try again.");
}

export const postFeedback = async (apiKey: string, requestId: string, rating: Rating, comment: string) =>
  // An empty comment is omitted: the API stores it as no comment.
  (await post("/feedback", apiKey, { request_id: requestId, rating, comment: comment || undefined })).json();
