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
  await page.getByRole("button", { name: "Send" }).click();

  await expect(page.getByText("Loosen the lug nuts before jacking the car 1.")).toBeVisible();
  await expect(page.getByText("aventro_manual.pdf · page 12")).toBeHidden();
  await page.getByRole("button", { name: /2 sources/ }).click();
  await expect(page.getByText("aventro_manual.pdf · page 12")).toBeVisible();

  await page.getByRole("button", { name: "Helpful", exact: true }).click();
  await expect(page.getByText(/feedback recorded/)).toBeVisible();

  await page.getByLabel("Question").fill("And how tight?");
  await page.getByLabel("Question").press("Enter");
  await expect(page.getByText("Loosen the lug nuts before jacking the car 1.")).toHaveCount(2);

  // On a phone the actions sit behind the menu button.
  if (isMobile) await page.getByRole("button", { name: "Menu" }).click();
  await expect(page.getByText("Memory · 2 of 5 turns")).toBeVisible();
  await page.getByRole("button", { name: "Clear chat & memory" }).click();
  await expect(page.getByText("Memory · 0 of 5 turns")).toBeAttached();
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
