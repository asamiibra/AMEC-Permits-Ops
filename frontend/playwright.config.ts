import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./browser-e2e",
  // Retired historical contracts are catalogued in the final-universal-closure
  // classification artifacts and exercised only by their replacement gates.
  testIgnore: [
    "**/expansion-e3-e4.spec.ts",
    "**/expansion-e5-e6.spec.ts",
    "**/issues-deeplink-final.spec.ts",
    "**/persona-issues-notifications.spec.ts",
    "**/pre-client-shell.spec.ts",
    "**/pre-g10-control-paths.spec.ts",
    "**/workflow-first.spec.ts",
  ],
  use: { headless: true, baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:5173" },
  ...(process.env.PLAYWRIGHT_BASE_URL ? {} : { webServer: { command: "npm run dev -- --host 127.0.0.1", url: "http://127.0.0.1:5173", reuseExistingServer: true } }),
});
