import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Documents } from "./Documents";

const KEY = "test-key-0123456789";
const json = (body: object, status = 200) => ({ status, body: JSON.stringify(body) });
const listed = (...docs: Array<[string, number]>) => json({ documents: docs.map(([name, chunks]) => ({ name, chunks })) });

function mockFetch(...responses: Array<{ status: number; body: string }>) {
  const fetch = vi.fn();
  for (const r of responses) fetch.mockResolvedValueOnce(new Response(r.body, { status: r.status }));
  vi.stubGlobal("fetch", fetch);
  return fetch;
}

function open(onUnauthorized = vi.fn()) {
  render(<Documents apiKey={KEY} onUnauthorized={onUnauthorized} />);
  const details = screen.getByText("Documents").closest("details")!;
  details.open = true;
  fireEvent(details, new Event("toggle"));
  return onUnauthorized;
}

const pick = (name: string) =>
  fireEvent.change(screen.getByLabelText("PDF to upload"), {
    target: { files: [new File(["%PDF-1.4"], name, { type: "application/pdf" })] },
  });

describe("Documents", () => {
  it("loads the list only when opened, with the key", async () => {
    const fetch = mockFetch(listed(["manual.pdf", 12]));
    render(<Documents apiKey={KEY} onUnauthorized={vi.fn()} />);
    expect(fetch).not.toHaveBeenCalled();

    const details = screen.getByText("Documents").closest("details")!;
    details.open = true;
    fireEvent(details, new Event("toggle"));
    expect(await screen.findByText("manual.pdf")).toBeTruthy();
    expect(screen.getByText("12 chunks")).toBeTruthy();
    const [path, init] = fetch.mock.calls[0];
    expect(path).toBe("/documents");
    expect(init.headers.Authorization).toBe(`Bearer ${KEY}`);
  });

  it("uploads the picked PDF as multipart, reports the chunks and refreshes the list", async () => {
    const fetch = mockFetch(listed(), json({ chunks_created: 7 }), listed(["new.pdf", 7]));
    open();
    await screen.findByText("No documents yet.");

    pick("new.pdf");
    expect(await screen.findByText("new.pdf: 7 chunks indexed.")).toBeTruthy();
    expect(screen.getByText("new.pdf")).toBeTruthy();
    const [path, init] = fetch.mock.calls[1];
    expect([path, init.method]).toEqual(["/documents", "POST"]);
    expect((init.body as FormData).get("file")).toBeInstanceOf(File);
    expect(init.headers["Content-Type"]).toBeUndefined(); // the browser sets the multipart boundary
  });

  it("shows why the server rejected an upload", async () => {
    mockFetch(listed(), json({ detail: "Document rejected: possible prompt injection detected (override)" }, 422));
    open();
    await screen.findByText("No documents yet.");
    pick("bad.pdf");
    expect((await screen.findByRole("alert")).textContent).toMatch(/possible prompt injection/);
  });

  it("deletes only after confirmation", async () => {
    const confirm = vi.fn(() => false);
    vi.stubGlobal("confirm", confirm);
    const fetch = mockFetch(listed(["my manual.pdf", 3]), json({ chunks_deleted: 3 }), listed());
    open();
    fireEvent.click(await screen.findByRole("button", { name: "Delete my manual.pdf" }));
    expect(confirm).toHaveBeenCalledOnce();
    expect(fetch).toHaveBeenCalledTimes(1);

    confirm.mockReturnValue(true);
    fireEvent.click(screen.getByRole("button", { name: "Delete my manual.pdf" }));
    expect(await screen.findByText("my manual.pdf deleted.")).toBeTruthy();
    expect(fetch.mock.calls[1][0]).toBe("/documents/my%20manual.pdf");
    expect(fetch.mock.calls[1][1].method).toBe("DELETE");
    expect(screen.getByText("No documents yet.")).toBeTruthy();
  });

  it("renders document names as plain text", async () => {
    const name = '<img src=x onerror="alert(1)">.pdf';
    mockFetch(listed([name, 1]));
    open();
    expect(await screen.findByText(name)).toBeTruthy();
    expect(document.querySelector("img")).toBeNull();
  });

  it("hands a rejected key back to the app", async () => {
    mockFetch({ status: 401, body: "{}" });
    const onUnauthorized = open();
    await vi.waitFor(() => expect(onUnauthorized).toHaveBeenCalledWith("The API key was rejected. Enter it again."));
  });
});
