import { expect, test } from "@playwright/test";

const projectId = "b8c8bd41-c06a-40cf-94e2-8e1af763303a";

test("Owner can operate the real Completion / As-Built workspace", async ({ page }) => {
  await page.addInitScript(() => sessionStorage.setItem("proposalops-role", "SYSTEM_ADMIN"));
  await page.goto("/completion");
  await expect(page.getByRole("heading", { name: "Completion scopes" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Start Completion" })).toBeVisible();
  await page.screenshot({ path: "../artifacts/completion-asbuilt-closure/browser-screenshots/completion-overview-closure.png", fullPage: true });

  await page.getByRole("button", { name: "Start Completion" }).click();
  await expect(page.getByRole("heading", { name: "Choose a completed construction scope" })).toBeVisible();
  await page.getByLabel("Project").selectOption(projectId);
  await page.getByLabel("Construction execution").selectOption({ label: "BROWSER-COMPLETION-20260813 · COMPLETED" });
  await page.getByRole("button", { name: "Start Completion / As-Built" }).click();

  await expect(page.getByRole("heading", { name: "Completion / As-Built workspace" })).toBeVisible();
  await expect(page.getByText("Human checkpoints remain active")).toBeVisible();
  await expect(page.getByRole("button", { name: "Overview" })).toBeVisible();

  await page.getByRole("button", { name: "As-Built Drawings" }).click();
  await expect(page.getByRole("heading", { name: "As-Built Drawings" })).toBeVisible();
  await page.screenshot({ path: "../artifacts/completion-asbuilt-closure/browser-screenshots/completion-asbuilt-baseline-closure.png", fullPage: true });

  await page.getByRole("button", { name: "Variance Review" }).click();
  await expect(page.getByRole("heading", { name: "Variance Review" })).toBeVisible();
  await page.screenshot({ path: "../artifacts/completion-asbuilt-closure/browser-screenshots/completion-variance-closure.png", fullPage: true });

  await page.getByRole("button", { name: "Requirements / Evidence" }).click();
  await expect(page.getByRole("heading", { name: "Requirements / Evidence" })).toBeVisible();
  await page.getByRole("button", { name: "Forms" }).click();
  await expect(page.getByRole("heading", { name: "Forms" })).toBeVisible();
  await page.getByRole("button", { name: "Reports" }).click();
  await expect(page.getByRole("heading", { name: "Reports" })).toBeVisible();

  await page.getByRole("button", { name: "Preparation / Precheck" }).click();
  await expect(page.getByRole("heading", { name: "Preparation / Precheck" })).toBeVisible();
  await page.screenshot({ path: "../artifacts/completion-asbuilt-closure/browser-screenshots/completion-precheck-closure.png", fullPage: true });

  await page.getByRole("button", { name: "Submission History" }).click();
  await expect(page.getByRole("heading", { name: "Submission History" })).toBeVisible();
  await page.screenshot({ path: "../artifacts/completion-asbuilt-closure/browser-screenshots/completion-submission-history-closure.png", fullPage: true });

  await page.getByRole("button", { name: "Completion Outcome" }).click();
  await expect(page.getByRole("heading", { name: "Completion Outcome" })).toBeVisible();
  await expect(page.getByText("No HandoverPackage is created by Completion.")).toBeVisible();
  await page.screenshot({ path: "../artifacts/completion-asbuilt-closure/browser-screenshots/completion-outcome-closure.png", fullPage: true });
});
