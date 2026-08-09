import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./browser-real-stack",
  timeout: 45_000,
  expect: { timeout: 10_000 },
  use: { headless: true, baseURL: "http://127.0.0.1:5173", trace: "retain-on-failure" },
  webServer: { command: "npm run dev -- --host 127.0.0.1", url: "http://127.0.0.1:5173", reuseExistingServer: true },
  reporter: [["list"], ["json", { outputFile: "../artifacts/pre-client-final-closure/real-stack-playwright.json" }]],
});
