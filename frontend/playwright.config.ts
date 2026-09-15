import { defineConfig } from "@playwright/test";

const port = process.env.PLAYWRIGHT_PORT || "5173";
const baseURL = process.env.PLAYWRIGHT_BASE_URL || `http://127.0.0.1:${port}`;

export default defineConfig({
  testDir: "./browser-e2e",
  // Retired historical contracts are catalogued in the final-universal-closure
  // classification artifacts and exercised only by their replacement gates.
  testIgnore: [
    "**/expansion-e3-e4.spec.ts",
    "**/expansion-e5-e6.spec.ts",
    "**/pre-client-shell.spec.ts",
    "**/pre-g10-control-paths.spec.ts",
    "**/workflow-first.spec.ts",
  ],
  use: { headless: true, baseURL },
  ...(process.env.PLAYWRIGHT_BASE_URL ? {} : { webServer: { command: `npm run dev -- --host 127.0.0.1 --port ${port}`, url: baseURL, reuseExistingServer: false } }),
});
