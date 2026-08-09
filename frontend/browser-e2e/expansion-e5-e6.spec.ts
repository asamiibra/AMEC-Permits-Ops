import { test, expect } from "@playwright/test";

const project = { id: "project-e5-e6", project_number: "SYN-PROJ-0001", project_name: "Synthetic Engineering Closeout" };
const review = { id: "review-e5", status: "READY_FOR_ENGINEER_REVIEW", current_drawing_version_id: "drawing-v1-hash-abc", current_scope_id: "scope-e5" };
const readiness = { evaluation: { state: "READY_FOR_HUMAN_APPROVAL", checks: [{ key: "deliverables", status: "PASS" }] } };

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => sessionStorage.setItem("permitops-role", "SYSTEM_ADMIN"));
  await page.route("**/api/**", async route => {
    const path = new URL(route.request().url()).pathname;
    let body: any = {};
    if (path === "/api/projects") body = [project];
    else if (path === "/api/applications") body = [];
    else if (path === "/api/reconciliation/governance") body = { environment_badge: "SYNTHETIC PROTOTYPE" };
    else if (path === `/api/projects/${project.id}/engineering-reviews`) body = [review];
    else if (path === `/api/projects/${project.id}/handover-readiness`) body = readiness;
    await route.fulfill({ json: body });
  });
});

test("E5/E6 navigation is visible", async ({ page }) => { await page.goto("/engineering-closeout"); await expect(page.getByRole("button", { name: "Engineering & Closeout" })).toBeVisible(); });
test("project context is selectable", async ({ page }) => { await page.goto("/engineering-closeout"); await expect(page.getByLabel("Project context")).toHaveValue(project.id); await expect(page.getByLabel("Project context")).toContainText("SYN-PROJ-0001 · Synthetic Engineering Closeout"); });
test("engineering page identifies bounded workflow", async ({ page }) => { await page.goto("/engineering-closeout"); await expect(page.getByRole("heading", { name: "Engineering & Commercial Closeout" })).toBeVisible(); await expect(page.getByText("E5 · E6 BOUNDED WORKFLOW")).toBeVisible(); });
test("engineering review is advisory only", async ({ page }) => { await page.goto("/engineering-closeout"); await expect(page.getByText("ADVISORY ONLY")).toBeVisible(); await expect(page.getByText("AI PROPOSED ≠ ENGINEER ACCEPTED")).toBeVisible(); });
test("drawing identity is displayed", async ({ page }) => { await page.goto("/engineering-closeout"); await expect(page.getByText("drawing-v1-hash-abc")).toBeVisible(); await expect(page.getByText("PINNED DOCUMENT VERSION REQUIRED")).not.toBeVisible(); });
test("human applicability scope is displayed", async ({ page }) => { await page.goto("/engineering-closeout"); await expect(page.getByText("CONFIGURED / HUMAN APPLICABILITY")).toBeVisible(); });
test("compliance and comment sheets are explicit", async ({ page }) => { await page.goto("/engineering-closeout"); await expect(page.getByText("Compliance Review Sheet")).toBeVisible(); await expect(page.getByText("Comment Sheet")).toBeVisible(); });
test("observed block time is explicit", async ({ page }) => { await page.goto("/engineering-closeout"); await expect(page.getByText("Observed Block-Time")).toBeVisible(); });
test("drawing revision loop is visible", async ({ page }) => { await page.goto("/engineering-closeout"); await expect(page.getByText("Drawing V1 → numbered comments → corrected drawing V2 → material-change invalidation → re-review.")).toBeVisible(); });
test("finance decision keeps human or configured authority", async ({ page }) => { await page.goto("/engineering-closeout"); await expect(page.getByText("HUMAN_DECISION / CONFIGURED_RULE")).toBeVisible(); });
test("finance route is generic and bounded", async ({ page }) => { await page.goto("/engineering-closeout"); await expect(page.getByText("GENERIC_FINANCE_HANDOFF")).toBeVisible(); await expect(page.getByText("TRACK / DRAFT / HANDOFF")).toBeVisible(); });
test("unknown invoice due date is not called late", async ({ page }) => { await page.goto("/engineering-closeout"); await expect(page.getByText("DUE_DATE_UNKNOWN / NEEDS_REVIEW when unconfigured")).toBeVisible(); });
test("handover readiness is shown before release", async ({ page }) => { await page.goto("/engineering-closeout"); await expect(page.getByText("READY_FOR_HUMAN_APPROVAL")).toBeVisible(); await expect(page.getByText("Handover Form / Output")).toBeVisible(); });
test("human send and no accounting write boundaries are visible", async ({ page }) => { await page.goto("/engineering-closeout"); await expect(page.getByText("HUMAN_SEND · NO ACCOUNTING WRITE")).toBeVisible(); await expect(page.getByText("Accounting ledger posting")).toBeVisible(); });
test("boundary register defers government submission and auto close", async ({ page }) => { await page.goto("/engineering-closeout"); await expect(page.getByText("Government final submission")).toBeVisible(); await expect(page.getByText("Automatic project closure")).toBeVisible(); });
