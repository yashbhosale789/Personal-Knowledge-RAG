import react from "@vitejs/plugin-react";
import type { Plugin } from "vite";
import { defineConfig } from "vitest/config";

// The API key sits in sessionStorage: no script may load from, or send data to, another origin.
const CSP = [
  "default-src 'self'",
  "script-src 'self'",
  "style-src 'self'",
  "connect-src 'self'",
  "img-src 'self'",
  "object-src 'none'",
  "base-uri 'none'",
  "form-action 'self'",
].join("; ");

// Build only: the dev server injects an inline React Refresh script that this policy blocks.
const csp: Plugin = {
  name: "csp-meta",
  apply: "build",
  transformIndexHtml: () => [
    { tag: "meta", attrs: { "http-equiv": "Content-Security-Policy", content: CSP }, injectTo: "head-prepend" },
  ],
};

const api = "http://localhost:8000";

export default defineConfig({
  plugins: [react(), csp],
  server: { proxy: { "/query": api, "/feedback": api } },
  test: { environment: "jsdom", include: ["src/**/*.test.tsx"], setupFiles: ["src/test-setup.ts"] },
});
