import { defineConfig, devices } from "@playwright/test";

// Runs against the production build (`npm run build` first), so the CSP is exercised too.
export default defineConfig({
  testDir: "e2e",
  webServer: { command: "npm run preview -- --port 4173 --strictPort", port: 4173 },
  use: { baseURL: "http://localhost:4173" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
});
