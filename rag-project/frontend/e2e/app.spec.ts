import { expect, test } from "@playwright/test";
import { answer, REQUEST_ID, sse } from "../src/fixtures";

const KEY = "test-key-0123456789";

test("ask a question, read the cited answer, rate it", async ({ page }) => {
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

  await expect(page.getByText(/Loosen the lug nuts.*\[SOURCE 1\]/)).toBeVisible();
  await expect(page.getByText(/\[SOURCE 1\] aventro_manual\.pdf, page 12 · cited/)).toBeVisible();

  await page.getByRole("button", { name: /^👍 Helpful/ }).click();
  await page.getByLabel("Comment (optional)").fill("clear steps");
  await page.getByRole("button", { name: "Send feedback" }).click();
  await expect(page.getByText(/Feedback recorded/)).toBeVisible();

  expect(sent).toEqual([
    { path: "/query/stream", auth: `Bearer ${KEY}`, body: { query: "How do I change a tyre?" } },
    { path: "/feedback", auth: `Bearer ${KEY}`, body: { request_id: REQUEST_ID, rating: "up", comment: "clear steps" } },
  ]);
  // Usable at this viewport: nothing forces sideways scrolling.
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  expect(errors).toEqual([]);
});
