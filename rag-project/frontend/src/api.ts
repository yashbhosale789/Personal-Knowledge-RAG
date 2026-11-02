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
  rewritten_query: string | null;
  latency_ms: number;
  outcome: string | null;
  confidence: string | null;
  sufficiency: { sufficient: boolean; reason: string; tier: string } | null;
  citation_check: { grounded: boolean; unsupported_claims: string[]; reason: string; tier: string } | null;
  chunks: Chunk[];
}

export type Rating = "up" | "down";

/** One remembered chat turn (api/models/requests.py Turn): no sources, so memory stays small. */
export interface Turn {
  query: string;
  rewritten_query: string | null;
  answer: string;
}

// Mirror config.HISTORY_TURNS and HISTORY_ANSWER_CHARS; the API rejects anything larger.
export const MEMORY_TURNS = 5;
export const MEMORY_ANSWER_CHARS = 500;

// Clips by code point so an emoji is never cut in half.
const clip = (text: string, max: number) => Array.from(text).slice(0, max).join("");

/** Appends a finished answer to the memory, keeping the newest MEMORY_TURNS turns. */
export const remember = (memory: Turn[], query: string, result: QueryResponse): Turn[] =>
  [
    ...memory,
    {
      query,
      rewritten_query: result.rewritten_query && clip(result.rewritten_query, 2000),
      answer: clip(result.answer, MEMORY_ANSWER_CHARS),
    },
  ].slice(-MEMORY_TURNS);

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
  409: "Another document is being processed. Try again shortly.",
  413: "The file is larger than the 10 MB upload limit.",
};

// The API's own message (e.g. why a document was rejected), when it sent a plain string.
async function detail(res: Response): Promise<string | undefined> {
  try {
    const body = await res.json();
    return typeof body?.detail === "string" ? body.detail : undefined;
  } catch {
    return undefined;
  }
}

async function request(path: string, apiKey: string, init: RequestInit = {}): Promise<Response> {
  let res: Response;
  try {
    res = await fetch(path, { ...init, headers: { ...init.headers, Authorization: `Bearer ${apiKey}` } });
  } catch {
    throw new ApiError(0, "Network error: the server could not be reached.");
  }
  if (!res.ok) {
    const message = MESSAGES[res.status] ?? (await detail(res)) ?? `Request failed (${res.status}).`;
    throw new ApiError(res.status, message);
  }
  return res;
}

const post = (path: string, apiKey: string, body: object) =>
  request(path, apiKey, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

/** Streams the answer to onToken as it is generated; resolves with the `final` event. */
export async function streamQuery(
  apiKey: string,
  query: string,
  history: Turn[],
  onToken: (text: string) => void,
): Promise<QueryResponse> {
  const res = await post("/query/stream", apiKey, { query, history });
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

/** GET /documents (api/models/responses.py DocumentInfo). */
export interface DocumentInfo {
  name: string;
  chunks: number;
}

export const listDocuments = async (apiKey: string): Promise<DocumentInfo[]> =>
  (await (await request("/documents", apiKey)).json()).documents;

/** Resolves with the number of chunks indexed. A document with the same name is replaced. */
export async function uploadDocument(apiKey: string, file: File): Promise<number> {
  const form = new FormData();
  form.append("file", file);
  return (await (await request("/documents", apiKey, { method: "POST", body: form })).json()).chunks_created;
}

export const deleteDocument = async (apiKey: string, name: string): Promise<void> => {
  await request(`/documents/${encodeURIComponent(name)}`, apiKey, { method: "DELETE" });
};
