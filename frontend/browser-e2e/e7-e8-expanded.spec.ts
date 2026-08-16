import { test, expect } from "@playwright/test";

const project = { id: "project-e7", project_number: "SYN-E7-0001", project_name: "Synthetic Unified Project", municipality: "Doha", permit_type: "Building Permit", status: "ACTIVE", assigned_engineer: "Omar Haddad" };
const items = [
  { id: "task-bd", domain: "PROPOSAL", title: "Review incoming RFQ", business_context: "Tender or client source is waiting for commercial intake.", reference: "SYN-RFQ-E7", assigned_team: "Business Development", stage: "New Proposal Intake", status: "OPEN", blocking: false, deep_link: "/opportunities/opp-e7", cta_label: "Open Proposal" },
  { id: "task-owner", domain: "SYSTEM", title: "Follow up missing document", business_context: "The owner follow-up remains open in the shared work context.", reference: "SYN-E7-0001", assigned_team: "Owner", stage: "Source integrity", status: "OPEN", blocking: false, deep_link: "/work/opp-e7", cta_label: "Review source" },
  { id: "task-engineering", domain: "PERMIT", title: "Review engineering comment", business_context: "A canonical drawing revision blocker must be resolved.", reference: project.project_number, assigned_team: "Engineering", stage: "Issue resolution", status: "BLOCKED", blocking: true, deep_link: `/proposals-contracts/${project.id}/comments-and-corrections`, cta_label: "Open Permit" },
  { id: "task-permit", domain: "PERMIT", title: "Coordinate permit handoff", business_context: "The downstream Permit handoff is ready for Engineering review.", reference: project.project_number, assigned_team: "Engineering", stage: "Permit review", status: "ACKNOWLEDGED", blocking: false, deep_link: `/proposals-contracts/${project.id}/project-and-sources`, cta_label: "Open Permit" },
];

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => sessionStorage.setItem("permitops-role", "SYSTEM_ADMIN"));
  await page.route("**/api/**", async route => {
    const path = new URL(route.request().url()).pathname;
    let body: any = {};
    if (path === "/api/projects") body = [project];
    else if (path === "/api/applications") body = [{ id: "app-e7", project_id: project.id, external_request_number: "SYN-APP-E7", application_status: "RETURNED", repetition_count: 1, municipality: "Doha", permit_type: "Building Permit" }];
    else if (path === "/api/reconciliation/governance") body = { environment_badge: "SYNTHETIC PROTOTYPE" };
    else if (path === "/api/work") body = { persona: "OWNER", filters: { team: "all", domain: "all", kpi: "all" }, summary: { needs_action: 3, waiting_review: 1, blocked: 1, overdue: 0 }, items, handoffs: [], recent_changes: [], total_visible: items.length, context_visible_count: items.length, unfiltered_visible_count: items.length, has_unassigned: false, projection: "AMEC Work", synthetic_only: true };
    else if (path === "/api/findings") body = { findings: [] };
    else if (path === "/api/tasks") body = { tasks: [] };
    else if (path === "/api/notifications") body = { notifications: [] };
    else if (path === "/api/role-context") body = { mode: "SYNTHETIC_DEMO", demo_as: true, self_role_switch_allowed: true };
    await route.fulfill({ json: body });
  });
});

test("AMEC Work opens with the canonical prioritized worklist", async ({ page }) => { await page.goto("/work"); await expect(page.getByRole("heading", { name: "What needs attention" })).toBeVisible(); await expect(page.getByText("One prioritized worklist across proposals, contracts, permits, and handoffs.")).toBeVisible(); });
test("synthetic boundary is explicit", async ({ page }) => { await page.goto("/work"); await expect(page.locator(".amec-work-page").getByText("SYNTHETIC PROTOTYPE", { exact: true })).toBeVisible(); await expect(page.getByText("Simulated integrations").first()).toBeVisible(); });
test("Demo as persona control is visible", async ({ page }) => { await page.goto("/work"); await expect(page.getByLabel("Persona")).toBeVisible(); await expect(page.getByLabel("Persona").locator("option")).toHaveText(["Owner", "Business Development", "Engineering"]); });
test("current persona and work filters exist", async ({ page }) => { await page.goto("/work"); await expect(page.getByLabel("Persona").locator("option")).toHaveCount(3); await expect(page.getByLabel("Work").locator("option")).toHaveText(["All work", "Proposals", "Contracts", "Permits", "System"]); });
test("Needs Action KPI is visible", async ({ page }) => { await page.goto("/work"); await expect(page.getByRole("button", { name: "Needs Action" })).toBeVisible(); });
test("Waiting for Review KPI is visible", async ({ page }) => { await page.goto("/work"); await expect(page.getByRole("button", { name: "Waiting for Review" })).toBeVisible(); });
test("Blocked KPI is visible", async ({ page }) => { await page.goto("/work"); await expect(page.getByRole("button", { name: "Blocked" })).toBeVisible(); });
test("Overdue KPI is visible", async ({ page }) => { await page.goto("/work"); await expect(page.getByRole("button", { name: "Overdue" })).toBeVisible(); });
test("Proposal domain filter is visible", async ({ page }) => { await page.goto("/work"); await expect(page.getByLabel("Work", { exact: true })).toContainText("Proposals"); });
test("Contract domain filter is visible", async ({ page }) => { await page.goto("/work"); await expect(page.getByLabel("Work", { exact: true })).toContainText("Contracts"); });
test("BD task is visible in the shared queue", async ({ page }) => { await page.goto("/work"); await expect(page.getByText("Review incoming RFQ")).toBeVisible(); });
test("Admin task is visible in the shared queue", async ({ page }) => { await page.goto("/work"); await expect(page.getByText("Follow up missing document")).toBeVisible(); });
test("Engineering task is visible in the shared queue", async ({ page }) => { await page.goto("/work"); await expect(page.getByText("Review engineering comment")).toBeVisible(); });
test("Permit task is visible in the shared queue", async ({ page }) => { await page.goto("/work"); await expect(page.getByText("Coordinate permit handoff")).toBeVisible(); });
test("work cards show current business context and stage", async ({ page }) => { await page.goto("/work"); await expect(page.getByText("A canonical drawing revision blocker must be resolved.")).toBeVisible(); await expect(page.getByText("Issue resolution")).toBeVisible(); });
test("current owner teams are shown on work cards", async ({ page }) => { await page.goto("/work"); await expect(page.locator(".amec-work-card").getByText("Business Development", { exact: true })).toBeVisible(); await expect(page.locator(".amec-work-card").getByText("Engineering", { exact: true }).first()).toBeVisible(); });
test("blocked work state is shown", async ({ page }) => { await page.goto("/work"); await expect(page.getByText("Blocking", { exact: true }).first()).toBeVisible(); });
test("deep links are exposed for work items", async ({ page }) => { await page.goto("/work"); await expect(page.locator("a", { hasText: /Open Proposal|Open Contract|Open Permit|Review source|Review draft/ }).first()).toHaveAttribute("href", /work|proposals|contracts|opportunities|engineering|permits|issues|notifications/); });
test("Business Development persona filters the worklist", async ({ page }) => { await page.goto("/work"); await page.getByLabel("Persona").selectOption("COMMERCIAL_APPROVER"); await expect(page.getByLabel("Persona")).toHaveValue("COMMERCIAL_APPROVER"); await expect(page.getByText("Review incoming RFQ")).toBeVisible(); });
test("Engineering persona is selectable", async ({ page }) => { await page.goto("/work"); await page.getByLabel("Persona").selectOption("RESPONSIBLE_ENGINEER"); await expect(page.getByLabel("Persona")).toHaveValue("RESPONSIBLE_ENGINEER"); });
test("current reference and stage are shown", async ({ page }) => { await page.goto("/work"); await expect(page.getByText("SYN-RFQ-E7", { exact: true })).toBeVisible(); await expect(page.getByText("New Proposal Intake", { exact: true })).toBeVisible(); });
test("human submission boundary remains visible", async ({ page }) => { await page.goto("/work"); await expect(page.getByText("Human-controlled transitions").first()).toBeVisible(); });
test("external send remains human-controlled", async ({ page }) => { await page.goto("/work"); await expect(page.getByText("Test data only").first()).toBeVisible(); await expect(page.getByText("Simulated integrations").first()).toBeVisible(); });
test("Proposals & Contracts remains reachable from the Operating Guide", async ({ page }) => { await page.goto("/operating-guide"); await page.getByRole("button", { name: "Open Proposals & Contracts" }).click(); await expect(page).toHaveURL(/\/proposals-contracts$/); });
test("Issues navigation remains reachable", async ({ page }) => { await page.goto("/work"); await page.getByRole("navigation").getByRole("button", { name: "Issues" }).click(); await expect(page).toHaveURL(/\/issues$/); });
test("Issues and Notifications are separate current surfaces", async ({ page }) => { await page.goto("/work"); await page.getByRole("navigation").getByRole("button", { name: "Issues" }).click(); await expect(page).toHaveURL(/\/issues$/); await page.getByRole("navigation").getByRole("button", { name: "Notifications" }).click(); await expect(page).toHaveURL(/\/notifications$/); });
test("operational boundary is explicit on the current shell", async ({ page }) => { await page.goto("/work"); await expect(page.getByText("SYNTHETIC PROTOTYPE").first()).toBeVisible(); await expect(page.getByText("Simulated integrations").first()).toBeVisible(); });
