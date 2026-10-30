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

function saveKey() {
  fireEvent.change(screen.getByLabelText("API key"), { target: { value: KEY } });
  fireEvent.click(screen.getByRole("button", { name: "Save key" }));
}

function ask(question = "How do I change a tyre?") {
  fireEvent.change(screen.getByLabelText("Question"), { target: { value: question } });
  fireEvent.click(screen.getByRole("button", { name: "Ask" }));
}

describe("App", () => {
  it("keeps the key in sessionStorage only and sends it as a Bearer token", async () => {
    const fetch = mockFetch(streamed());
    render(<App />);
    saveKey();
    expect(sessionStorage.getItem("rag-api-key")).toBe(KEY);
    expect(localStorage.length).toBe(0);

    ask();
    await screen.findByText(/before jacking the car/);
    const [path, init] = fetch.mock.calls[0];
    expect(path).toBe("/query/stream");
    expect(init.headers.Authorization).toBe(`Bearer ${KEY}`);
    expect(JSON.parse(init.body)).toEqual({ query: "How do I change a tyre?" });
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
    expect(screen.queryByRole("button", { name: "Send feedback" })).toBeNull();
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

  it("sends a rating with an optional comment for this request ID", async () => {
    sessionStorage.setItem("rag-api-key", KEY);
    const fetch = mockFetch(streamed(), { status: 200, body: JSON.stringify({ status: "recorded" }) });
    render(<App />);
    ask();
    await screen.findByText(/before jacking the car/);

    const send = screen.getByRole("button", { name: "Send feedback" }) as HTMLButtonElement;
    expect(send.disabled).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: /Not helpful/ }));
    fireEvent.change(screen.getByLabelText("Comment (optional)"), { target: { value: "  wrong torque  " } });
    fireEvent.click(send);

    await screen.findByText(/Feedback recorded/);
    const [path, init] = fetch.mock.calls[1];
    expect(path).toBe("/feedback");
    expect(JSON.parse(init.body)).toEqual({ request_id: REQUEST_ID, rating: "down", comment: "wrong torque" });
  });

  it("omits an empty comment and explains an expired answer", async () => {
    sessionStorage.setItem("rag-api-key", KEY);
    const fetch = mockFetch(streamed(), { status: 404 });
    render(<App />);
    ask();
    await screen.findByText(/before jacking the car/);

    fireEvent.click(screen.getByRole("button", { name: /^👍 Helpful/ }));
    fireEvent.click(screen.getByRole("button", { name: "Send feedback" }));

    await screen.findByText(/can no longer be rated/);
    expect(JSON.parse(fetch.mock.calls[1][1].body)).toEqual({ request_id: REQUEST_ID, rating: "up" });
  });
});
