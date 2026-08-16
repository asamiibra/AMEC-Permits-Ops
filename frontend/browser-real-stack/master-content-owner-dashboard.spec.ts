import { expect, test } from "@playwright/test";

const ownerHeaders = { "X-Dev-Role": "SYSTEM_ADMIN" };

test("Owner Dashboard golden paths use the real API and propagate a governed Engineering change", async ({ page }) => {
  const suffix = Date.now().toString(36);
  const formRef = `E2E-F-${suffix}`;
  const engineeringRef = `E2E-E-${suffix}`;
  const term = `E2E verification term ${suffix}`;

  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: "Content Library", level: 2 })).toBeVisible();
  for (const label of ["Forms", "Reports", "Engineering Works", "Definitions"]) {
    await expect(page.getByRole("heading", { name: label, level: 3 })).toBeVisible();
  }

  await page.getByRole("button", { name: "New Form" }).click();
  await page.getByLabel("Title / Name").fill("Verification Form");
  await page.getByLabel("Reference").first().fill(formRef);
  await page.getByRole("dialog").getByLabel("Category").selectOption({ label: "General" });
  await page.getByLabel("Description").fill("Created through the Owner Dashboard real-stack path.");
  await page.getByLabel("File").setInputFiles({ name: "browser-form.txt", mimeType: "text/plain", buffer: Buffer.from("browser form v1") });
  await page.getByRole("button", { name: "Create Form" }).click();
  await expect(page.getByText(formRef, { exact: true })).toBeVisible();

  const formRow = page.getByRole("row").filter({ hasText: formRef });
  await formRow.getByRole("button", { name: "Edit" }).click();
  await page.getByLabel("Why are you making this change?").fill("Browser metadata revision");
  await page.getByLabel("File").setInputFiles({ name: "browser-form-v2.txt", mimeType: "text/plain", buffer: Buffer.from("browser form v2") });
  await page.getByRole("button", { name: "Save as New Version" }).click();
  await expect(formRow).toContainText("Version 2");
  await formRow.getByRole("button", { name: "History" }).click();
  await expect(page.getByText(/IMMUTABLE HISTORY/)).toBeVisible();
  await page.getByRole("dialog").getByLabel("Close").click();

  await page.getByRole("button", { name: "New Engineering Work" }).click();
  await page.getByLabel("Title / Name").fill("Verification Engineering Work");
  await page.getByLabel("Reference").first().fill(engineeringRef);
  await page.getByRole("dialog").getByLabel("Category").selectOption({ label: "Technical Reference" });
  await page.getByLabel("Engineering Source Type").selectOption({ label: "TECHNICAL REFERENCE" });
  await page.getByLabel("Description").fill("Synthetic Engineering Works source for propagation proof.");
  await page.getByLabel("File").setInputFiles({ name: "browser-engineering.txt", mimeType: "text/plain", buffer: Buffer.from("engineering v1") });
  await page.getByRole("button", { name: "Create Engineering Work" }).click();
  await expect(page.getByText(engineeringRef, { exact: true })).toBeVisible();

  const engineeringRow = page.getByRole("row").filter({ hasText: engineeringRef });
  const engineeringItem = await page.request.get(`/api/master-content?content_type=ENGINEERING_WORK&q=${engineeringRef}`, { headers: ownerHeaders });
  expect(engineeringItem.ok()).toBeTruthy();
  const item = (await engineeringItem.json())[0];
  const projectsResponse = await page.request.get("/api/projects", { headers: ownerHeaders });
  expect(projectsResponse.ok()).toBeTruthy();
  const projects = await projectsResponse.json();
  const project = (await Promise.all(projects.map(async (candidate: { id: string }) => {
    const response = await page.request.get(`/api/projects/${candidate.id}`, { headers: ownerHeaders });
    return response.ok() ? response.json() : null;
  }))).find((candidate: { applications?: unknown[] } | null) => (candidate?.applications?.length || 0) > 0);
  expect(project).toBeTruthy();
  const dependencyResponse = await page.request.post(`/api/master-content/${item.id}/dependencies`, { headers: { ...ownerHeaders, "Content-Type": "application/json" }, data: { downstream_type: "EngineeringReview", downstream_id: `browser-review-${suffix}`, project_id: project.id } });
  expect(dependencyResponse.ok()).toBeTruthy();

  await engineeringRow.getByRole("button", { name: "Edit" }).click();
  await page.getByLabel("Why are you making this change?").fill("Browser material engineering revision");
  await page.getByLabel("File").setInputFiles({ name: "browser-engineering-v2.txt", mimeType: "text/plain", buffer: Buffer.from("engineering v2") });
  await page.getByRole("button", { name: "Save as New Version" }).click();
  await expect(engineeringRow).toContainText("Version 2");

  const propagationResponse = await page.request.get(`/api/master-content/${item.id}/propagation`, { headers: ownerHeaders });
  expect(propagationResponse.ok()).toBeTruthy();
  const propagation = await propagationResponse.json();
  const currentItemResponse = await page.request.get(`/api/master-content/${item.id}`, { headers: ownerHeaders });
  const currentItem = await currentItemResponse.json();
  expect(propagation.dependencies[0].status).toBe("NEEDS_REVALIDATION");
  expect(propagation.lineage.length).toBeGreaterThanOrEqual(2);
  expect(propagation.events.some((event: { materiality: string; new_version_id: string }) => event.materiality === "MATERIAL" && event.new_version_id === currentItem.current_version_id)).toBeTruthy();

  const issues = await page.request.get("/api/issues?persona=ENGINEERING", { headers: { "X-Dev-Role": "RESPONSIBLE_ENGINEER" } });
  expect(issues.ok()).toBeTruthy();
  expect((await issues.json()).issues.some((issue: { title: string }) => issue.title.startsWith(engineeringRef))).toBeTruthy();
  const work = await page.request.get("/api/work?team=ENGINEERING", { headers: { "X-Dev-Role": "RESPONSIBLE_ENGINEER" } });
  expect(work.ok()).toBeTruthy();
  expect((await work.json()).items.some((entry: { source_type: string; title: string }) => entry.source_type === "WORKFLOW_TASK" && entry.title.startsWith("Revalidate"))).toBeTruthy();
  const notifications = await page.request.get("/api/notifications?persona=ENGINEERING&domain=MASTER_CONTENT", { headers: { "X-Dev-Role": "RESPONSIBLE_ENGINEER" } });
  expect(notifications.ok()).toBeTruthy();
  expect((await notifications.json()).notifications.some((entry: { event_type: string }) => entry.event_type === "MASTER_CONTENT_VERSION_PROMOTED")).toBeTruthy();

  await page.getByRole("button", { name: "New Definition" }).click();
  await page.getByLabel("Word / Term").fill(term);
  await page.getByRole("dialog").getByLabel("Category").selectOption({ label: "Client" });
  await page.getByLabel("Description").fill("Structured definition created through the Owner Dashboard.");
  await page.getByRole("button", { name: "Create Definition" }).click();
  await expect(page.getByText(term, { exact: true })).toBeVisible();
  const lookup = await page.request.get(`/api/definitions/lookup/${encodeURIComponent(term)}`, { headers: ownerHeaders });
  expect(lookup.ok()).toBeTruthy();
  expect((await lookup.json()).term).toBe(term);

  const revalidateResponse = await page.request.post(`/api/master-content/dependencies/${propagation.dependencies[0].id}/revalidate`, { headers: ownerHeaders });
  expect(revalidateResponse.ok()).toBeTruthy();
  expect((await revalidateResponse.json()).status).toBe("CURRENT");
});
