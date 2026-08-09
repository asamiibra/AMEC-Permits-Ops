import { test, expect } from "@playwright/test";

const project = { id: "project-e7", project_number: "SYN-E7-0001", project_name: "Synthetic Unified Project", municipality: "Doha", permit_type: "Building Permit", status: "ACTIVE", assigned_engineer: "Omar Haddad" };
const items = [
  { id: "task-bd", assistant_id: "BD_ASSISTANT", title: "Review incoming RFQ", context_type: "OPPORTUNITY", context_id: "opp-e7", owner_role: "COMMERCIAL_APPROVER", status: "OPEN", next_action: "REVIEW_AND_ASSIGN", next_action_details: { label: "Review and assign", reason: "Shared opportunity context is waiting for the commercial approver.", deep_link: "/opportunities/opp-e7", deterministic: true }, evidence_summary: { source_revision_ids: ["rfq-r01"] } },
  { id: "task-admin", assistant_id: "ADMIN_ASSISTANT", title: "Follow up missing document", context_type: "CHECKLIST", context_id: "opp-e7", owner_role: "ADMIN_PROJECT_COORDINATOR", status: "OPEN", next_action: "PREPARE_CONTRACT", next_action_details: { label: "Prepare contract", reason: "The admin checklist remains open.", deep_link: "/work/opp-e7", deterministic: true }, evidence_summary: { source_revision_ids: ["checklist-r02"] } },
  { id: "task-engineering", assistant_id: "ENGINEERING_REVIEW_ASSISTANT", title: "Review engineering comment", context_type: "ENGINEERING_REVIEW", context_id: project.id, owner_role: "AUTHORIZED_ENGINEER", status: "BLOCKED", blocking: true, next_action: "RESOLVE_BLOCKER", next_action_details: { label: "Resolve blocker", reason: "A canonical drawing revision blocker must be resolved.", deep_link: `/engineering-closeout/${project.id}`, deterministic: true }, evidence_summary: { source_revision_ids: ["drawing-r03"] } },
  { id: "task-permit", assistant_id: "PROJECT_PERMIT_COORDINATION_ASSISTANT", title: "Coordinate permit handoff", context_type: "PROJECT", context_id: project.id, owner_role: "PERMIT_PREPARER", status: "ACKNOWLEDGED", next_action: "BEGIN_ASSISTED_WORK", next_action_details: { label: "Begin assisted work", reason: "The shared permit handoff was accepted.", deep_link: `/permits/${project.id}`, deterministic: true }, evidence_summary: { source_revision_ids: ["permit-r04"] } },
];

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => sessionStorage.setItem("permitops-role", "SYSTEM_ADMIN"));
  await page.route("**/api/**", async route => {
    const path = new URL(route.request().url()).pathname;
    let body: any = {};
    if (path === "/api/projects") body = [project];
    else if (path === "/api/applications") body = [{ id: "app-e7", project_id: project.id, external_request_number: "SYN-APP-E7", application_status: "RETURNED", repetition_count: 1, municipality: "Doha", permit_type: "Building Permit" }];
    else if (path === "/api/reconciliation/governance") body = { environment_badge: "SYNTHETIC PROTOTYPE" };
    else if (path === "/api/my-work") body = { assistant_ids: ["BD_ASSISTANT", "ADMIN_ASSISTANT", "ENGINEERING_REVIEW_ASSISTANT", "PROJECT_PERMIT_COORDINATION_ASSISTANT"], summary: { action_required: 4, reviews_waiting: 2, blocked_work: 1, authority_changes: 1, communication_drafts: 2, delivery_failures: 0 }, items, communications: [{ id: "comm-e7", communication_type: "MISSING_DOCUMENT", status: "HUMAN_REVIEW" }], issues: [{ id: "issue-e7", source_type: "ENGINEERING", title: "Drawing revision blocker" }], handoffs: [], canonical_queue: "WorkflowTask", next_action_policy: "DETERMINISTIC_SHARED_STATE", human_send_required: true, synthetic_only: true };
    else if (path === "/api/findings") body = { findings: [] };
    else if (path === "/api/tasks") body = { tasks: [] };
    else if (path === "/api/notifications") body = { notifications: [] };
    else if (path === "/api/role-context") body = { mode: "SYNTHETIC_DEMO", demo_as: true, self_role_switch_allowed: true };
    await route.fulfill({ json: body });
  });
});

test("E7 My Work opens with the unified operating surface", async ({ page }) => { await page.goto("/work"); await expect(page.getByRole("heading", { name: "Resume permit work" })).toBeVisible(); await expect(page.getByRole("heading", { name: "My Work across shared operating context" })).toBeVisible(); });
test("synthetic boundary is explicit", async ({ page }) => { await page.goto("/work"); await expect(page.getByText("DEMO AS · SYNTHETIC ONLY", { exact: false })).toBeVisible(); await expect(page.getByText("HUMAN_SEND required", { exact: false })).toBeVisible(); });
test("Demo as role control is visible", async ({ page }) => { await page.goto("/work"); await expect(page.getByLabel("Role", { exact: true })).toContainText("Demo as"); });
test("four assistant lens options exist", async ({ page }) => { await page.goto("/work"); await expect(page.getByLabel("Assistant lens")).toContainText("BD"); await expect(page.getByLabel("Assistant lens")).toContainText("Admin"); await expect(page.getByLabel("Assistant lens")).toContainText("Engineering"); await expect(page.getByLabel("Assistant lens")).toContainText("Project / Permit"); });
test("Action Required summary is visible", async ({ page }) => { await page.goto("/work"); await expect(page.getByText("Action Required", { exact: true })).toBeVisible(); });
test("Reviews Waiting summary is visible", async ({ page }) => { await page.goto("/work"); await expect(page.getByText("Reviews Waiting", { exact: true })).toBeVisible(); });
test("Blocked Work summary is visible", async ({ page }) => { await page.goto("/work"); await expect(page.getByText("Blocked Work", { exact: true })).toBeVisible(); });
test("Authority Changes summary is visible", async ({ page }) => { await page.goto("/work"); await expect(page.getByText("Authority Changes", { exact: true })).toBeVisible(); });
test("Communication Drafts summary is visible", async ({ page }) => { await page.goto("/work"); await expect(page.getByText("Communication Drafts", { exact: true })).toBeVisible(); });
test("Delivery Failures summary is visible", async ({ page }) => { await page.goto("/work"); await expect(page.getByText("Delivery Failures", { exact: true })).toBeVisible(); });
test("BD task is visible in the shared queue", async ({ page }) => { await page.goto("/work"); await expect(page.getByText("Review incoming RFQ")).toBeVisible(); });
test("Admin task is visible in the shared queue", async ({ page }) => { await page.goto("/work"); await expect(page.getByText("Follow up missing document")).toBeVisible(); });
test("Engineering task is visible in the shared queue", async ({ page }) => { await page.goto("/work"); await expect(page.getByText("Review engineering comment")).toBeVisible(); });
test("Permit task is visible in the shared queue", async ({ page }) => { await page.goto("/work"); await expect(page.getByText("Coordinate permit handoff")).toBeVisible(); });
test("deterministic NextAction label is shown", async ({ page }) => { await page.goto("/work"); await expect(page.getByText("NextAction: Resolve blocker", { exact: false })).toBeVisible(); await expect(page.getByText("NextAction: Begin assisted work", { exact: false })).toBeVisible(); });
test("owner role is shown on work cards", async ({ page }) => { await page.goto("/work"); await expect(page.getByText(/AUTHORIZED_ENGINEER/).first()).toBeVisible(); await expect(page.getByText(/PERMIT_PREPARER/).first()).toBeVisible(); });
test("blocked task badge is shown", async ({ page }) => { await page.goto("/work"); await expect(page.getByText("BLOCKED", { exact: true }).first()).toBeVisible(); });
test("deep links are exposed for tasks", async ({ page }) => { await page.goto("/work"); await expect(page.locator("a", { hasText: "Open work" }).first()).toHaveAttribute("href", /work|opportunities|engineering|permits/); });
test("BD assistant lens filters the queue", async ({ page }) => { await page.goto("/work"); await page.getByLabel("Assistant lens").selectOption("BD_ASSISTANT"); await expect(page.getByText("Review incoming RFQ")).toBeVisible(); });
test("Engineering assistant lens is selectable", async ({ page }) => { await page.goto("/work"); await page.getByLabel("Assistant lens").selectOption("ENGINEERING_REVIEW_ASSISTANT"); await expect(page.getByLabel("Assistant lens")).toHaveValue("ENGINEERING_REVIEW_ASSISTANT"); });
test("shared evidence revision is shown", async ({ page }) => { await page.goto("/work"); await expect(page.getByText("drawing-r03", { exact: true })).toBeVisible(); await expect(page.getByText("Source family: WorkflowTask", { exact: false }).first()).toBeVisible(); });
test("human authority badge remains visible", async ({ page }) => { await page.goto("/work"); await expect(page.getByText("HUMAN AUTHORITY REQUIRED").first()).toBeVisible(); });
test("HUMAN_SEND communication state is visible", async ({ page }) => { await page.goto("/work"); await expect(page.getByText("HUMAN_SEND", { exact: false }).first()).toBeVisible(); });
test("existing Opportunities navigation remains reachable", async ({ page }) => { await page.goto("/work"); await page.getByRole("navigation").getByRole("button", { name: "Opportunities" }).click(); await expect(page.getByRole("button", { name: "Opportunities" }).first()).toBeVisible(); });
test("existing Engineering and Closeout navigation remains reachable", async ({ page }) => { await page.goto("/work"); await page.getByRole("navigation").getByRole("button", { name: "Engineering & Closeout" }).click(); await expect(page.getByRole("button", { name: "Engineering & Closeout" }).first()).toBeVisible(); });
test("issues source-family panel is visible", async ({ page }) => { await page.goto("/work"); await expect(page.getByText("Issues by source family", { exact: true })).toBeVisible(); await expect(page.getByText("ENGINEERING · Drawing revision blocker", { exact: true })).toBeVisible(); });
test("communications source panel is visible", async ({ page }) => { await page.goto("/work"); await expect(page.getByText("Communication drafts", { exact: true })).toBeVisible(); await expect(page.getByText("MISSING_DOCUMENT · HUMAN_REVIEW · HUMAN_SEND", { exact: true })).toBeVisible(); });
test("production role switching is not implied by the synthetic UI", async ({ page }) => { await page.goto("/work"); await expect(page.getByText("SYNTHETIC ONLY", { exact: false }).first()).toBeVisible(); await expect(page.getByText("No portal writes", { exact: false }).first()).toBeVisible(); });
