import { expect, test } from "@playwright/test";

const form = {
  id: "form-1",
  serial_number: 1,
  ref: "F-0001",
  content_type: "FORM",
  title: "Permit application form",
  category: { id: "general", label: "General" },
  description: "A reusable permit application form.",
  used_in: ["BD"],
  owner_status: "Current",
  version_status: "CURRENT",
  version: 2,
  current_source_filename: "permit-application.pdf",
  review_note: null,
  versions: [
    { id: "version-2", version: 2, status: "CURRENT", file_name: "permit-application.pdf", updated_by: "Owner", updated_at: "2026-08-30T10:00:00Z" },
  ],
  governance: {
    profile: { artifact_kind: "AUTHORITY_FORM", content_ownership_class: "EXTERNAL_OFFICIAL" },
    readiness: { state: "MANUAL_USE_READY", blocking_reasons: [], warnings: [] },
    badges: ["EXTERNAL_OFFICIAL"],
  },
};

const contentItems = [
  { id: "report-1", serial_number: 1, ref: "R-0001", content_type: "REPORT", title: "Permit review report", category: { id: "report", label: "Reports" }, description: "Reusable reporting reference.", used_in: ["BD"], version_status: "CURRENT", version: 1, current_source_filename: "permit-review-report.pdf", versions: [] },
  { id: "engineering-1", serial_number: 1, ref: "E-0001", content_type: "ENGINEERING_WORK", title: "Engineering review guide", category: { id: "engineering", label: "Engineering" }, description: "Controlled engineering reference.", used_in: ["ENGINEERING"], version_status: "CURRENT", version: 1, source_type_code: "TECHNICAL_REFERENCE", engineering_metadata: { discipline: "GENERAL", authority: "Hidden from Owner" }, current_source_filename: "engineering-review-guide.pdf", versions: [] },
];

const definition = { id: "definition-1", serial_number: 1, ref: "D-0001", term: "Current application", category: "Permit", description: "A submitted application under review.", used_in: ["PERMIT"], status: "CURRENT", revision: 1, revisions: [] };

test.describe("Owner Content Library product acceptance", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => sessionStorage.setItem("proposalops-role", "SYSTEM_ADMIN"));
    await page.route("**/api/**", async (route) => {
      const url = new URL(route.request().url());
      const path = url.pathname;
      if (path.startsWith("/api/retrieval/query")) {
        await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
        return;
      }
      let body: unknown = {};
      if (path === "/api/master-content" || path === "/api/master-content/categories") {
        body = path === "/api/master-content"
          ? (url.searchParams.get("content_type") === "FORM" ? [form] : contentItems)
          : [];
      } else if (path === "/api/master-content/form-1") {
        body = form;
      } else if (path === "/api/definitions") {
        body = [definition];
      } else if (path === "/api/definitions/definition-1") {
        body = definition;
      } else if (path === "/api/dashboard-v2/catalogs") {
        body = { external_bodies: [], jurisdictions: [], service_types: [], lifecycle_phases: [] };
      } else if (path === "/api/dashboard-inputs") {
        body = { summary: { confirmed: 1, remaining: 0, technical_remaining: 0, ready: true }, groups: [], items: [] };
      }
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
    });
  });

  for (const [name, viewport] of [
    ["desktop", { width: 1440, height: 1000 }],
    ["mobile", { width: 390, height: 844 }],
  ] as const) {
    test(`${name} Dashboard and library surfaces are owner-ready`, async ({ page }, testInfo) => {
      await page.setViewportSize(viewport);
      let retrievalRequested = false;
      page.on("request", (request) => {
        if (request.url().includes("/api/retrieval/query")) retrievalRequested = true;
      });
      await page.goto("/dashboard");
      await expect(page.getByTestId("current-dashboard")).toHaveAttribute("data-dashboard-root", "content-library");
      for (const heading of ["Forms", "Reports", "Engineering Works", "Definitions"]) {
        await expect(page.getByRole("heading", { name: heading })).toBeVisible();
      }
      for (const forbidden of ["Canonical control plane", "Governance Overview", "Advanced governance filters", "Source & Authority", "Form automation governance", "Purpose bindings", "Hidden from Owner"]) {
        await expect(page.getByText(forbidden, { exact: false })).toHaveCount(0);
      }
      await page.getByLabel("Search master content").fill("permit");
      await expect(page.getByText("Permit application form", { exact: true })).toBeVisible();
      expect(retrievalRequested).toBe(false);
      await page.screenshot({ path: testInfo.outputPath(`owner-content-library-${name}.png`), fullPage: true });

      await page.getByRole("button", { name: "Open" }).first().click();
      await expect(page.getByRole("heading", { name: /F-0001 · Permit application form/ })).toBeVisible();
      const formDetails = page.getByRole("dialog", { name: /F-0001 · Permit application form/ });
      await expect(page.getByText("Current source file")).toBeVisible();
      await expect(page.getByText("Version History")).toBeVisible();
      await expect(page.getByRole("link", { name: "Download current source" })).toBeVisible();
      await expect(formDetails.getByRole("button", { name: "Modify" })).toBeVisible();
      await expect(formDetails.getByRole("button", { name: "Upload version" })).toBeVisible();
      for (const forbidden of ["Source & Authority", "Quality & Sensitivity", "Source Sections", "Readiness", "Regulatory applicability", "Policy and technical source lineage", "Form automation governance", "Evaluate readiness", "Create mapping draft", "Validate draft"]) {
        await expect(page.getByText(forbidden, { exact: false })).toHaveCount(0);
      }
      await page.screenshot({ path: testInfo.outputPath(`owner-form-details-${name}.png`), fullPage: true });
      await formDetails.getByText("Close", { exact: true }).click();
      const engineeringSection = page.getByTestId("dashboard-engineering_work");
      await engineeringSection.getByRole("button", { name: "Edit" }).click();
      await expect(page.getByLabel("Engineering Source Type")).toBeVisible();
      await expect(page.getByLabel("Engineering Discipline")).toBeVisible();
      await expect(page.getByLabel("Engineering metadata")).toHaveCount(0);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
    });
  }
});
