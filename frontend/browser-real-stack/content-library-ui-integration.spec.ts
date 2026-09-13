import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test.describe("Content Library first-class UI integration", () => {
  test("canonical route, four libraries, aliases, and specialized route boundary", async ({ page }) => {
    await page.goto("/content-library");
    await expect(page).toHaveURL(/\/content-library$/);
    await expect(page.getByRole("heading", { name: "Content Library", level: 2 })).toBeVisible();
    for (const heading of ["Forms", "Reports", "Engineering Works", "Definitions"]) {
      await expect(page.getByRole("heading", { name: heading, level: 3 })).toBeVisible();
    }
    for (const alias of ["/dashboard", "/dashboard-v2", "/library", "/master-content"]) {
      await page.goto(alias);
      await expect(page).toHaveURL(/\/content-library$/);
    }
    await page.goto("/dashboard/inputs-go-live");
    await expect(page).toHaveURL(/\/dashboard\/inputs-go-live$/);
  });

  test("library deep links and persona-scoped navigation remain usable on mobile", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/content-library/reports");
    await expect(page.getByRole("heading", { name: "Reports", level: 3 })).toBeVisible();
    await expect(page.getByRole("link", { name: /Reports/ })).toHaveAttribute("aria-current", "page");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
    await page.getByRole("button", { name: "Open navigation" }).click();
    await expect(page.getByRole("navigation", { name: "Mobile primary navigation" })).toContainText("Content Library");
    await page.getByRole("button", { name: "Close navigation" }).click();

    for (const role of ["COMMERCIAL_APPROVER", "RESPONSIBLE_ENGINEER"] as const) {
      await page.getByLabel("Persona").selectOption(role);
      await page.getByRole("button", { name: "Open navigation" }).click();
      await expect(page.getByRole("navigation", { name: "Mobile primary navigation" }).getByRole("button", { name: "Content Library" })).toBeVisible();
      await expect(page.getByLabel("Persona")).toHaveValue(role);
      await page.getByRole("button", { name: "Close navigation" }).click();
    }

    const axe = await new AxeBuilder({ page }).analyze();
    expect(axe.violations.filter((item) => ["serious", "critical"].includes(item.impact || ""))).toEqual([]);
  });

  test("opens a canonical deep link and exercises Drawer keyboard boundaries", async ({ page, request }) => {
    await page.addInitScript(() => sessionStorage.setItem("proposalops-role", "SYSTEM_ADMIN"));
    const response = await request.get("/api/master-content?content_type=FORM", { headers: { "X-Dev-Role": "SYSTEM_ADMIN" } });
    expect(response.ok()).toBeTruthy();
    const item = (await response.json())[0];
    expect(item?.id).toBeTruthy();
    await page.goto(`/content-library?content=${encodeURIComponent(item.id)}`);
    await expect(page).toHaveURL(new RegExp(`/content-library\\?content=${item.id}$`));
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await expect(dialog).toHaveAttribute("aria-labelledby", "content-drawer-title");
    await expect(page.locator(":focus")).toHaveAttribute("aria-label", "Close");
    await page.keyboard.press("Tab");
    await page.keyboard.press("Shift+Tab");
    await expect(page.locator(":focus")).toHaveAttribute("aria-label", "Close");
    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);
  });

  test("exposes the typed read-only Source18 official-form projection", async ({ request }) => {
    const listing = await request.get("/api/master-content/official-forms", { headers: { "X-Dev-Role": "SYSTEM_ADMIN" } });
    expect(listing.ok()).toBeTruthy();
    const listingBody = await listing.json();
    expect(listingBody.projection_type).toBe("SOURCE18_OFFICIAL_FORM_READ_ONLY");
    expect(listingBody.authority_owner).toBe("SOURCE18");
    expect(listingBody.read_only).toBe(true);
    expect(Array.isArray(listingBody.items)).toBe(true);
    expect(listingBody.items.length).toBeGreaterThan(0);
    for (const item of listingBody.items) {
      expect(item.projection_type).toBe("SOURCE18_OFFICIAL_FORM_READ_ONLY");
      expect(item.source18?.transaction_id).toBeTruthy();
      expect(item.source18?.authority_case_id).toBeTruthy();
      expect(item.document_version?.id).toBeTruthy();
      expect(item.document_version?.sha256).toMatch(/^[a-f0-9]{64}$/);
      expect(item.provenance?.source_system).toBe("SOURCE18");
      expect(item.provenance?.source_hash).toBe(item.document_version.sha256);
      expect(item.currentness?.state).toBe("CURRENT");
      expect(item.currentness?.reusable).toBe(true);
      expect(item.reuse?.allowed).toBe(true);
    }

    const resolving = await request.get("/api/master-content/official-forms/resolve", { headers: { "X-Dev-Role": "SYSTEM_ADMIN" } });
    expect(resolving.ok()).toBeTruthy();
    const resolvingBody = await resolving.json();
    expect(resolvingBody.truth).toBe("SOURCE18");
    expect(resolvingBody.status).toBe("RESOLVED");
    expect(resolvingBody.canonical_count).toBe(1);
    expect(resolvingBody.item.document_version.id).toBe(listingBody.items[0].document_version.id);
    expect(resolvingBody.item.document_version.sha256).toBe(listingBody.items[0].document_version.sha256);
  });

  test("Content Library Go-Live handoff is configurable and returns to the library", async ({ page }) => {
    await page.goto("/content-library");
    await page.getByRole("link", { name: "Inputs & Go-Live" }).click();
    await expect(page).toHaveURL(/\/dashboard\/inputs-go-live\?from=content-library$/);
    await expect(page.getByRole("button", { name: "Back to Content Library" })).toBeVisible();
    await page.getByRole("button", { name: "Back to Content Library" }).click();
    await expect(page).toHaveURL(/\/content-library$/);
  });
});
