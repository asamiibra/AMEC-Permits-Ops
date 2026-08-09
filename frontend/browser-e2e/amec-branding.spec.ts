import { test, expect } from "@playwright/test";

test("AMEC logo is consistent across the shell, My Work, About, and permit workspace", async ({ page }) => {
  for (const route of ["/work", "/about", "/permits/SYN-PROJ-0001/project-and-sources"]) {
    await page.goto(route);
    const logo = page.getByRole("img", { name: "AMEC — Art Mark Engineering Consultant" }).first();
    await expect(logo).toBeVisible();
    await expect(logo).toHaveAttribute("srcset", /amec-logo@3x\.png 3x/);
    await expect(logo).toHaveCSS("object-fit", "contain");
    expect(await logo.evaluate((element) => getComputedStyle(element).transform)).not.toContain("matrix(-1");
  }
  await page.goto("/work");
  await page.screenshot({ path: "../artifacts/production-readiness-ui/amec-my-work-desktop.png", fullPage: true });
  await page.goto("/about");
  await page.screenshot({ path: "../artifacts/production-readiness-ui/amec-about-desktop.png", fullPage: true });
  await page.goto("/permits/SYN-PROJ-0001/project-and-sources");
  await page.screenshot({ path: "../artifacts/production-readiness-ui/amec-permit-workspace-desktop.png", fullPage: true });
});

test("AMEC logo remains unmirrored and usable in Arabic mobile UI", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/work");
  const logo = page.locator('img[alt="AMEC — Art Mark Engineering Consultant"]:visible').first();
  await expect(logo).toBeVisible();
  await page.screenshot({ path: "../artifacts/production-readiness-ui/amec-my-work-mobile.png", fullPage: true });
  await page.goto("/about");
  await page.getByRole("button", { name: "العربي" }).click();
  await expect(page.locator("main.about-page")).toHaveAttribute("dir", "rtl");
  await expect(page.locator('img[alt="AMEC — Art Mark Engineering Consultant"]:visible').first()).toBeVisible();
  await page.screenshot({ path: "../artifacts/production-readiness-ui/amec-about-ar-eg-mobile.png", fullPage: true });
});
