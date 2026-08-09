import { test, expect } from "@playwright/test";

const projects = [
  { id: "p-0142", project_number: "GHCE-2026-0142", project_name: "Al Noor Villa", municipality: "Doha", permit_type: "Building Permit", status: "ACTIVE", assigned_engineer: "Omar Haddad" },
  { id: "p-0187", project_number: "GHCE-2026-0187", project_name: "West Bay Residence", municipality: "Doha", permit_type: "Building Permit", status: "ACTIVE", assigned_engineer: "Rana Faisal" },
];

test.beforeEach(async ({ page }) => {
  await page.route("**/api/projects", route => route.fulfill({ json: projects }));
  await page.route("**/api/applications", route => route.fulfill({ json: projects.map((p, i) => ({ id: `a-${i}`, project_id: p.id, external_request_number: `GHCE-APP-${i ? "0187" : "0142"}`, application_status: i ? "RETURNED" : "DRAFT", repetition_count: i, municipality: p.municipality, permit_type: p.permit_type })) }));
  await page.route("**/api/reconciliation/governance", route => route.fulfill({ json: { environment_badge: "SYNTHETIC PROTOTYPE" } }));
});

test("canonical project bootstrap and safety controls", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("SYNTHETIC PROTOTYPE", { exact: true })).toBeVisible();
  await expect(page.getByText("AMEC Engineering", { exact: true })).toBeVisible();
  await expect(page.getByText("HUMAN SUBMISSION REQUIRED").first()).toBeVisible();
  await page.getByRole("navigation").getByRole("button", { name: /Permits/ }).click();
  await expect(page.getByText("GHCE-2026-0142")).toBeVisible();
  await expect(page.getByText("GHCE-APP-0142")).toBeVisible();
  await expect(page.getByText("Current stage / status")).toBeVisible();
});
