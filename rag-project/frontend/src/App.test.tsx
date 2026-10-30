import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import App from "./App";
import { answer, REQUEST_ID } from "./fixtures";

const KEY = "test-key-0123456789";

function mockFetch(...responses: Array<{ status: number; body?: unknown }>) {
  const fetch = vi.fn();
  for (const r of responses) fetch.mockResolvedValueOnce(new Response(JSON.stringify(r.body ?? {}), { status: r.status }));
  vi.stubGlobal("fetch", fetch);
  return fetch;
}

function saveKey() {
  fireEvent.change(screen.getByLabelText("API key"), { target: { value: KEY } });
  fireEvent.click(screen.getByRole("button", { name: "Save key" }));
}

async function ask(question = "How do I change a tyre?") {
  fireEvent.change(screen.getByLabelText("Question"), { target: { value: question } });
  fireEvent.click(screen.getByRole("button", { name: "Ask" }));
}

describe("App", () => {
  it("keeps the key in sessionStorage only and sends it as a Bearer token", async () => {
    const fetch = mockFetch({ status: 200, body: answer() });
    render(<App />);
    saveKey();
    expect(sessionStorage.getItem("rag-api-key")).toBe(KEY);
    expect(localStorage.length).toBe(0);

    await ask();
    await screen.findByText(/Loosen the lug nuts/);
    const [path, init] = fetch.mock.calls[0];
    expect(path).toBe("/query");
    expect(init.headers.Authorization).toBe(`Bearer ${KEY}`);
    expect(JSON.parse(init.body)).toEqual({ query: "How do I change a tyre?" });
  });

  it("clears a rejected key and asks for it again", async () => {
    sessionStorage.setItem("rag-api-key", "wrong-key-0123456789");
    mockFetch({ status: 401 });
    render(<App />);
    await ask();
    expect((await screen.findByRole("alert")).textContent).toMatch(/API key was rejected/);
    expect(screen.getByLabelText("API key")).toBeTruthy();
    expect(sessionStorage.getItem("rag-api-key")).toBeNull();
  });

  it("shows server errors without losing the key", async () => {
    sessionStorage.setItem("rag-api-key", KEY);
    mockFetch({ status: 502 });
    render(<App />);
    await ask();
    expect((await screen.findByRole("alert")).textContent).toMatch(/Every LLM provider failed/);
    expect(sessionStorage.getItem("rag-api-key")).toBe(KEY);
  });

  it("sends a rating with an optional comment for this request ID", async () => {
    sessionStorage.setItem("rag-api-key", KEY);
    const fetch = mockFetch({ status: 200, body: answer() }, { status: 200, body: { status: "recorded" } });
    render(<App />);
    await ask();
    await screen.findByText(/Loosen the lug nuts/);

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
    const fetch = mockFetch({ status: 200, body: answer() }, { status: 404 });
    render(<App />);
    await ask();
    await screen.findByText(/Loosen the lug nuts/);

    fireEvent.click(screen.getByRole("button", { name: /^👍 Helpful/ }));
    fireEvent.click(screen.getByRole("button", { name: "Send feedback" }));

    await screen.findByText(/can no longer be rated/);
    expect(JSON.parse(fetch.mock.calls[1][1].body)).toEqual({ request_id: REQUEST_ID, rating: "up" });
  });
});
