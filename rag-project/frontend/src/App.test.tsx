import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import App from "./App";
import { answer, REQUEST_ID, sse } from "./fixtures";

const KEY = "test-key-0123456789";

function mockFetch(...responses: Array<{ status: number; body?: string }>) {
  const fetch = vi.fn();
  for (const r of responses) fetch.mockResolvedValueOnce(new Response(r.body ?? "{}", { status: r.status }));
  vi.stubGlobal("fetch", fetch);
  return fetch;
}

const streamed = (final = answer()) => ({ status: 200, body: sse(["Loosen the ", "lug nuts"], { final }) });
const sentBody = (fetch: ReturnType<typeof vi.fn>, call: number) => JSON.parse(fetch.mock.calls[call][1].body);

function saveKey() {
  fireEvent.change(screen.getByLabelText("API key"), { target: { value: KEY } });
  fireEvent.click(screen.getByRole("button", { name: "Save key" }));
}

function ask(question = "How do I change a tyre?") {
  fireEvent.change(screen.getByLabelText("Question"), { target: { value: question } });
  fireEvent.click(screen.getByRole("button", { name: "Send" }));
}

const answered = () => screen.findAllByText(/before jacking the car/);

describe("App", () => {
  it("keeps the key in sessionStorage only and sends it as a Bearer token", async () => {
    const fetch = mockFetch(streamed());
    render(<App />);
    saveKey();
    expect(sessionStorage.getItem("rag-api-key")).toBe(KEY);
    expect(localStorage.length).toBe(0);

    ask();
    await answered();
    const [path, init] = fetch.mock.calls[0];
    expect(path).toBe("/query/stream");
    expect(init.headers.Authorization).toBe(`Bearer ${KEY}`);
    expect(JSON.parse(init.body)).toEqual({ query: "How do I change a tyre?", history: [] });
  });

  it("shows the question as a chat message and sends on Enter", async () => {
    sessionStorage.setItem("rag-api-key", KEY);
    mockFetch(streamed());
    render(<App />);
    const box = screen.getByLabelText("Question");
    fireEvent.change(box, { target: { value: "How do I change a tyre?" } });
    fireEvent.keyDown(box, { key: "Enter" });
    expect(screen.getByText("How do I change a tyre?").className).toBe("user-msg");
    await answered();
    expect((box as HTMLTextAreaElement).value).toBe("");
  });

  it("replaces the streamed text with the final answer and its caveat", async () => {
    sessionStorage.setItem("rag-api-key", KEY);
    const final = answer({ answer: "Loosen the lug nuts.\n\n[Note: unverified.]", confidence: "low", outcome: "answer_low_confidence" });
    mockFetch(streamed(final));
    render(<App />);
    ask();
    expect((await screen.findByRole("status")).textContent).toMatch(/Low confidence/);
    expect(screen.getByText(/\[Note: unverified\.\]/)).toBeTruthy();
    expect(screen.queryByLabelText("Answer so far")).toBeNull();
  });

  it("keeps the partial answer visible when the stream breaks off", async () => {
    sessionStorage.setItem("rag-api-key", KEY);
    mockFetch({ status: 200, body: sse(["Loosen the "], { error: { status: 502, error: "The answer stream broke off. Try again." } }) });
    render(<App />);
    ask();
    expect((await screen.findByRole("alert")).textContent).toMatch(/broke off/);
    expect(screen.getByLabelText("Answer so far").textContent).toBe("Loosen the ");
    expect(screen.queryByRole("button", { name: "Helpful" })).toBeNull();
  });

  it("sends the remembered turns with a follow-up, and Clear chat keeps them", async () => {
    sessionStorage.setItem("rag-api-key", KEY);
    const fetch = mockFetch(streamed(), streamed(), streamed());
    render(<App />);
    ask();
    await answered();
    expect(screen.getByText(/Memory · 1 of 5 turns/)).toBeTruthy();

    ask("And how tight?");
    await screen.findByText("And how tight?");
    await vi.waitFor(() => expect(screen.getAllByText(/before jacking the car/)).toHaveLength(2));
    const turn = { query: "How do I change a tyre?", rewritten_query: "change a tyre", answer: answer().answer };
    expect(sentBody(fetch, 1)).toEqual({ query: "And how tight?", history: [turn] });

    fireEvent.click(screen.getByRole("button", { name: "Clear chat" }));
    expect(screen.queryByText("And how tight?")).toBeNull();
    expect(screen.getByText(/Memory · 2 of 5 turns/)).toBeTruthy();

    ask("What about the spare?");
    await answered();
    expect(sentBody(fetch, 2).history).toHaveLength(2);
  });

  it("Clear chat & memory forgets the earlier turns", async () => {
    sessionStorage.setItem("rag-api-key", KEY);
    const fetch = mockFetch(streamed(), streamed());
    render(<App />);
    ask();
    await answered();

    fireEvent.click(screen.getByRole("button", { name: "Clear chat & memory" }));
    expect(screen.getByText(/Memory · 0 of 5 turns/)).toBeTruthy();
    ask("And how tight?");
    await answered();
    expect(sentBody(fetch, 1)).toEqual({ query: "And how tight?", history: [] });
  });

  it("keeps upload and clear database disabled until the storage fix", () => {
    render(<App />);
    expect((screen.getByRole("button", { name: /Upload files/ }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: /Clear database/ }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("clears a rejected key and asks for it again", async () => {
    sessionStorage.setItem("rag-api-key", "wrong-key-0123456789");
    mockFetch({ status: 401 });
    render(<App />);
    ask();
    expect((await screen.findByRole("alert")).textContent).toMatch(/API key was rejected/);
    expect(screen.getByLabelText("API key")).toBeTruthy();
    expect(sessionStorage.getItem("rag-api-key")).toBeNull();
  });

  it("shows server errors without losing the key", async () => {
    sessionStorage.setItem("rag-api-key", KEY);
    mockFetch({ status: 503 });
    render(<App />);
    ask();
    expect((await screen.findByRole("alert")).textContent).toMatch(/starting or unavailable/);
    expect(sessionStorage.getItem("rag-api-key")).toBe(KEY);
  });

  it("sends a thumb at once, then an optional comment for this request ID", async () => {
    sessionStorage.setItem("rag-api-key", KEY);
    const ok = { status: 200, body: JSON.stringify({ status: "recorded" }) };
    const fetch = mockFetch(streamed(), ok, ok);
    render(<App />);
    ask();
    await answered();

    fireEvent.click(screen.getByRole("button", { name: "Not helpful" }));
    await screen.findByText(/feedback recorded/);
    expect(fetch.mock.calls[1][0]).toBe("/feedback");
    expect(sentBody(fetch, 1)).toEqual({ request_id: REQUEST_ID, rating: "down" });
    expect(screen.getByRole("button", { name: "Not helpful" }).getAttribute("aria-pressed")).toBe("true");

    fireEvent.click(screen.getByRole("button", { name: "Add a comment" }));
    fireEvent.change(screen.getByLabelText("Comment (optional)"), { target: { value: "  wrong torque  " } });
    fireEvent.click(screen.getByRole("button", { name: "Send feedback" }));
    await screen.findByText("Comment saved.");
    expect(sentBody(fetch, 2)).toEqual({ request_id: REQUEST_ID, rating: "down", comment: "wrong torque" });
  });

  it("explains an answer that can no longer be rated", async () => {
    sessionStorage.setItem("rag-api-key", KEY);
    mockFetch(streamed(), { status: 404 });
    render(<App />);
    ask();
    await answered();

    fireEvent.click(screen.getByRole("button", { name: "Helpful" }));
    await screen.findByText(/can no longer be rated/);
  });
});
