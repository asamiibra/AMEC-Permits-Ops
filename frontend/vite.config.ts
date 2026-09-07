import { fileURLToPath } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const apiProxyTarget =
  process.env.VITE_API_URL || "http://127.0.0.1:8000";

const mainHtml =
  fileURLToPath(
    new URL(
      "./index.html",
      import.meta.url,
    ),
  );

const redirectBridgeHtml =
  fileURLToPath(
    new URL(
      "./redirect.html",
      import.meta.url,
    ),
  );

export default defineConfig({
  // Keep SPA fallback behavior for ProposalOps routes. The production build
  // still has two HTML inputs so the MSAL redirect bridge is emitted.
  appType: "spa",
  plugins: [
    react(),
  ],
  build: {
    // Vite 8 uses Rolldown. rollupOptions remains a deprecated alias, so use
    // the native Vite 8 configuration surface for the two HTML entry points.
    rolldownOptions: {
      input: {
        main: mainHtml,
        redirect: redirectBridgeHtml,
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": apiProxyTarget,
      "/health": apiProxyTarget,
      "/mock-authority": apiProxyTarget,
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: "./tests/setup.ts",
    include: [
      "tests/**/*.{test,spec}.{js,ts,jsx,tsx}",
    ],
    exclude: [
      "browser-e2e/**",
      "browser-real-stack/**",
      "test-results/**",
      "artifacts/**",
      "dist/**",
      "coverage/**",
      "node_modules/**",
    ],
    pool: "forks",
    maxWorkers: 1,
    fileParallelism: false,
  },
});
