import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./browser-e2e",
  use: { headless: true, baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:5173" },
  ...(process.env.PLAYWRIGHT_BASE_URL ? {} : { webServer: { command: "npm run dev -- --host 127.0.0.1", url: "http://127.0.0.1:5173", reuseExistingServer: true } }),
});
