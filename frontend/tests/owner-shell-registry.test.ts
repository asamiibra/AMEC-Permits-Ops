import { describe, expect, it } from "vitest";
import {
  featureAvailability,
  getPrimaryNavigation,
  isDisabledTopLevelRoute,
  ownerShellAcceptance,
} from "../src/featureAvailability";
import { classifyPublicRoute } from "../src/domainOwnershipRoutes";

describe("Owner shell feature registry", () => {
  it("keeps the complete work-oriented shell and Home", () => {
    expect(Object.values(featureAvailability).filter(Boolean)).toHaveLength(9);
    expect(getPrimaryNavigation("OWNER_SPONSOR").map((item) => item.label)).toEqual([
      "Home",
      "My Work",
      "Opportunities & Proposals",
      "Contract & Mobilization",
      "Projects & Delivery",
      "Billing & Finance",
      "Content Library",
    ]);
    expect(ownerShellAcceptance.OWNER_PRIMARY_DESTINATION_COUNT).toBe(7);
  });

  it("lets OFF flags win over the Owner and demo SYSTEM_ADMIN aliases", () => {
    expect(featureAvailability.admin).toBe(true);
    expect(featureAvailability.inputsGoLive).toBe(false);
    expect(featureAvailability.notifications).toBe(false);
    expect(getPrimaryNavigation("SYSTEM_ADMIN")).not.toContainEqual(
      expect.objectContaining({ label: "Admin" }),
    );
    expect(isDisabledTopLevelRoute("/admin")).toBe(false);
    expect(isDisabledTopLevelRoute("/dashboard/inputs-go-live")).toBe(true);
    expect(isDisabledTopLevelRoute("/notifications")).toBe(false);
    expect(isDisabledTopLevelRoute("/construction/exec-1")).toBe(false);
  });

  it("enforces the positive public route allowlist", () => {
    expect(classifyPublicRoute("/home")).toMatchObject({ page: "home", allowed: true });
    expect(classifyPublicRoute("/opportunities/example")).toMatchObject({ page: "opportunities", allowed: true });
    expect(classifyPublicRoute("/contract-mobilization/contracts/example")).toMatchObject({ page: "contract-mobilization", allowed: true });
    expect(classifyPublicRoute("/billing/invoices/example")).toMatchObject({ page: "billing", allowed: true });
    expect(classifyPublicRoute("/master-content/forms")).toMatchObject({ page: "content-library", allowed: true });
    expect(classifyPublicRoute("/permits")).toMatchObject({ page: "project-delivery", allowed: true });
    expect(classifyPublicRoute("/issues/example")).toMatchObject({ page: "issues", allowed: true });
    expect(classifyPublicRoute("/notifications")).toMatchObject({ page: "notifications", allowed: true });
    for (const path of [
      "/admin/contracts",
      "/dashboard/inputs-go-live",
      "/unknown-route",
    ]) {
      expect(classifyPublicRoute(path)).toMatchObject({ page: "home", canonicalPath: "/home", allowed: false });
    }
  });
});
