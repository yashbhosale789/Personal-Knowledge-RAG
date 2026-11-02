import { expect, test } from "@playwright/test";
import { answer, REQUEST_ID, sse } from "../src/fixtures";

const KEY = "test-key-0123456789";

test("chat: ask, open the sources, rate, ask a follow-up with memory", async ({ page, isMobile }) => {
  // Any console error fails the test, which includes the CSP blocking the build's own code.
  const errors: string[] = [];
  page.on("console", (msg) => msg.type() === "error" && errors.push(msg.text()));
  page.on("pageerror", (err) => errors.push(err.message));

  const sent: Array<{ path: string; auth: string | undefined; body: unknown }> = [];
  await page.route(/\/(query\/stream|feedback)$/, async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    sent.push({ path, auth: request.headers()["authorization"], body: request.postDataJSON() });
    if (path === "/feedback") return route.fulfill({ json: { status: "recorded", request_id: REQUEST_ID } });
    await route.fulfill({
      contentType: "text/event-stream",
      body: sse(["Loosen the lug nuts ", "before jacking the car [SOURCE 1]."], { final: answer() }),
    });
  });

  await page.goto("/");
  await page.getByLabel("API key").fill(KEY);
  await page.getByRole("button", { name: "Save key" }).click();
  await page.getByLabel("Question").fill("How do I change a tyre?");
  await page.getByRole("button", { name: "Ask" }).click();

  await expect(page.getByText("Loosen the lug nuts before jacking the car1.")).toBeVisible();
  await expect(page.getByText("aventro_manual.pdf, p. 12")).toBeHidden();
  await page.getByRole("button", { name: /2 sources/ }).click();
  await expect(page.getByText("aventro_manual.pdf, p. 12")).toBeVisible();

  await page.getByRole("button", { name: "Helpful", exact: true }).click();
  await expect(page.getByText("thanks")).toBeVisible();

  await page.getByLabel("Question").fill("And how tight?");
  await page.getByLabel("Question").press("Enter");
  await expect(page.getByText("Loosen the lug nuts before jacking the car1.")).toHaveCount(2);

  // On a phone the actions sit behind the menu button.
  if (isMobile) await page.getByRole("button", { name: "Menu" }).click();
  await expect(page.getByText("memory 2/5 turns")).toBeVisible();
  await page.getByRole("button", { name: "Clear chat and memory" }).click();
  await expect(page.getByText("memory 0/5 turns")).toBeAttached();
  await expect(page.getByText("And how tight?")).toHaveCount(0);

  const turn = { query: "How do I change a tyre?", rewritten_query: "change a tyre", answer: answer().answer };
  expect(sent).toEqual([
    { path: "/query/stream", auth: `Bearer ${KEY}`, body: { query: "How do I change a tyre?", history: [] } },
    { path: "/feedback", auth: `Bearer ${KEY}`, body: { request_id: REQUEST_ID, rating: "up" } },
    { path: "/query/stream", auth: `Bearer ${KEY}`, body: { query: "And how tight?", history: [turn] } },
  ]);
  // Usable at this viewport: nothing forces sideways scrolling.
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  expect(errors).toEqual([]);
});

test("documents: list, upload a PDF, delete it after confirming", async ({ page, isMobile }) => {
  const errors: string[] = [];
  page.on("console", (msg) => msg.type() === "error" && errors.push(msg.text()));
  page.on("pageerror", (err) => errors.push(err.message));

  const long = "Owner's Manual - Adaptive Cruise Control and Lane Keeping Assist (2026 edition).pdf";
  // A committed corpus PDF; CI runs from rag-project/frontend.
  const upload = "Adjusting the Steering Wheel.pdf";
  let docs = [{ name: long, chunks: 40 }];
  const sent: Array<{ method: string; path: string; auth: string | undefined; multipart: boolean }> = [];
  await page.route(/\/documents(\/.*)?$/, async (route) => {
    const request = route.request();
    const path = decodeURIComponent(new URL(request.url()).pathname);
    const type = request.headers()["content-type"] ?? "";
    sent.push({ method: request.method(), path, auth: request.headers()["authorization"], multipart: type.startsWith("multipart/form-data") });
    if (request.method() === "POST") {
      docs = [...docs, { name: upload, chunks: 9 }];
      return route.fulfill({ json: { status: "success", file_path: upload, chunks_created: 9, message: "ok" } });
    }
    if (request.method() === "DELETE") {
      docs = docs.filter((d) => `/documents/${d.name}` !== path);
      return route.fulfill({ json: { status: "success", file_path: upload, chunks_deleted: 9, message: "ok" } });
    }
    await route.fulfill({ json: { documents: docs } });
  });

  await page.goto("/");
  await page.getByLabel("API key").fill(KEY);
  await page.getByRole("button", { name: "Save key" }).click();
  if (isMobile) await page.getByRole("button", { name: "Menu" }).click();

  await page.getByText("Documents", { exact: true }).click();
  await expect(page.getByText(long)).toBeVisible();
  await expect(page.getByText("40 chunks")).toBeVisible();

  await page.getByLabel("PDF to upload").setInputFiles(`../data/documents/${upload}`);
  await expect(page.getByText(`${upload}: 9 chunks indexed.`)).toBeVisible();

  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: `Delete ${upload}` }).click();
  await expect(page.getByText(`${upload} deleted.`)).toBeVisible();
  await expect(page.getByRole("button", { name: `Delete ${upload}` })).toHaveCount(0);

  const auth = `Bearer ${KEY}`;
  expect(sent).toEqual([
    { method: "GET", path: "/documents", auth, multipart: false },
    { method: "POST", path: "/documents", auth, multipart: true },
    { method: "GET", path: "/documents", auth, multipart: false },
    { method: "DELETE", path: `/documents/${upload}`, auth, multipart: false },
    { method: "GET", path: "/documents", auth, multipart: false },
  ]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  expect(errors).toEqual([]);
});
