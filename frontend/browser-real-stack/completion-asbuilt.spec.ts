import { expect, test } from "@playwright/test";

test("Owner can operate the real Completion / As-Built workspace", async ({ page }) => {
  await page.addInitScript(() => sessionStorage.setItem("proposalops-role", "SYSTEM_ADMIN"));
  await page.goto("/completion");
  await expect(page.getByRole("heading", { name: "Completion scopes" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Start Completion" })).toBeVisible();
  await page.screenshot({ path: "../artifacts/completion-asbuilt-closure/browser-screenshots/completion-overview-closure.png", fullPage: true });

  await page.getByRole("button", { name: "Start Completion" }).click();
  await expect(page.getByRole("heading", { name: "Choose a completed construction scope" })).toBeVisible();
  const projectsResponse = await page.request.get("/api/projects", { headers: { "X-Dev-Role": "SYSTEM_ADMIN" } });
  expect(projectsResponse.ok()).toBeTruthy();
  const projects = await projectsResponse.json();
  const projectDetails = await Promise.all(projects.map(async (project: { id: string }) => {
    const response = await page.request.get(`/api/projects/${project.id}`, { headers: { "X-Dev-Role": "SYSTEM_ADMIN" } });
    return response.ok() ? response.json() : null;
  }));
  const project = projectDetails.find((candidate: { applications?: unknown[] } | null) => (candidate?.applications?.length || 0) > 0) || projects[0];
  expect(project?.id).toBeTruthy();
  const fixtureResponse = await page.request.post(`/api/construction/test-support/completed-execution?project_id=${encodeURIComponent(project.id)}`, { headers: { "X-Dev-Role": "SYSTEM_ADMIN" } });
  expect(fixtureResponse.ok()).toBeTruthy();
  const execution = await fixtureResponse.json();
  await page.reload();
  await expect(page.getByRole("heading", { name: "Choose a completed construction scope" })).toBeVisible();
  await page.getByLabel("Project").selectOption(project.id);
  await page.getByLabel("Construction execution").selectOption(execution.id);
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
