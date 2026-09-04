import { expect, test } from "@playwright/test";

test.describe("clean handoff mobile navigation accessibility", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("passes the 25-condition keyboard, focus, semantics, and overflow matrix", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("domcontentloaded");

    const trigger = page.locator("button.mobile-nav-trigger");
    const drawer = page.locator(".mobile-nav-drawer");
    const close = page.locator("button.mobile-nav-close");
    const navItems = page.locator("#mobile-primary-navigation button");

    await trigger.focus();
    await expect(trigger).toHaveAccessibleName("Open navigation");
    await expect(trigger).toHaveAttribute("aria-expanded", "false");
    await expect(trigger).toHaveAttribute("aria-controls", "mobile-primary-navigation");
    await page.keyboard.press("Enter");
    await expect(drawer).toBeVisible();
    await expect(trigger).toHaveAttribute("aria-expanded", "true");
    await expect(drawer).toHaveRole("dialog");
    await expect(drawer).toHaveAttribute("aria-modal", "true");
    await expect(page.locator("#mobile-primary-navigation")).toBeVisible();
    await expect(close).toBeFocused();
    await expect(navItems).toHaveCount(12);
    await expect(page.locator(".main")).toHaveAttribute("inert", "");
    await expect(page.locator(".sidebar")).toHaveAttribute("inert", "");

    await page.keyboard.press("Shift+Tab");
    await expect(page.locator("#mobile-primary-navigation button").last()).toBeFocused();
    await page.keyboard.press("Tab");
    await expect(close).toBeFocused();
    const focusedLabels: string[] = [];
    for (let i = 0; i < 12; i += 1) {
      await page.keyboard.press("Tab");
      focusedLabels.push(await page.evaluate(() => document.activeElement?.getAttribute("aria-label") || ""));
    }
    expect(focusedLabels).toContain("Operating Guide");

    await page.keyboard.press("Escape");
    await expect(drawer).toBeHidden();
    await expect(trigger).toHaveAttribute("aria-expanded", "false");
    await expect(trigger).toBeFocused();
    await expect(page.locator(".main")).not.toHaveAttribute("inert");
    await expect(page.locator(".sidebar")).not.toHaveAttribute("inert");

    await page.keyboard.press("Enter");
    await expect(close).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(drawer).toBeHidden();
    await expect(trigger).toBeFocused();

    await page.keyboard.press("Enter");
    await expect(close).toBeFocused();
    await page.keyboard.press("Space");
    await expect(drawer).toBeHidden();
    await expect(trigger).toBeFocused();

    await page.keyboard.press("Enter");
    await expect(close).toBeFocused();
    await close.click();
    await expect(drawer).toBeHidden();
    await expect(trigger).toBeFocused();

    await page.keyboard.press("Enter");
    await expect(close).toBeFocused();
    await page.getByRole("button", { name: "Regulatory & Submissions" }).click();
    await expect(drawer).toBeHidden();
    await expect(page).toHaveURL(/\/permits$/);
    await expect(page.locator(".content")).toBeFocused();
    await expect(page.locator(".main")).not.toHaveAttribute("inert");
    await expect(page.locator("body")).not.toBeFocused();
    await expect(page.locator("html")).toHaveJSProperty("scrollWidth", await page.locator("html").evaluate((element) => element.clientWidth));
  });
});
