import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./browser-real-stack",
  // Historical global-Arabic, Permit Preparer, old permit-first, and pre-realignment
  // detail assertions are retired; current replacements are in the closure suite.
  testIgnore: [
    "**/accessibility.spec.ts",
    "**/issue-detail-final.spec.ts",
    "**/new-proposal-final.spec.ts",
    "**/owner-rehearsal.spec.ts",
    "**/proposals-contracts-final.spec.ts",
    "**/stage1-confirm-project-sources.spec.ts",
    "**/visual-qa.spec.ts",
  ],
  timeout: 45_000,
  expect: { timeout: 10_000 },
  use: { headless: true, baseURL: process.env.BASE_URL || "http://127.0.0.1:5173", trace: "retain-on-failure" },
  webServer: process.env.BASE_URL ? undefined : { command: "npm run dev -- --host 127.0.0.1", url: "http://127.0.0.1:5173", reuseExistingServer: true },
  reporter: [["list"], ["json", { outputFile: "../artifacts/pre-client-final-closure/real-stack-playwright.json" }]],
});
