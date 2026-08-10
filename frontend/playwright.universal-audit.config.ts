import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./browser-real-stack",
  timeout: 45_000,
  expect: { timeout: 10_000 },
  use: { headless: true, baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:5173", trace: "retain-on-failure" },
  reporter: [["list"]],
});
