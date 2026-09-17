import { describe, expect, it } from "vitest";
import {
  featureAvailability,
  getPrimaryNavigation,
  isDisabledTopLevelRoute,
  ownerShellAcceptance,
} from "../src/featureAvailability";
import { classifyPublicRoute } from "../src/domainOwnershipRoutes";

describe("Owner shell feature registry", () => {
  it("keeps exactly four active modules and Home", () => {
    expect(Object.values(featureAvailability).filter(Boolean)).toHaveLength(4);
    expect(getPrimaryNavigation("SYSTEM_ADMIN").map((item) => item.label)).toEqual([
      "Home",
      "Content Library",
      "Proposals V1",
      "Contracts",
      "Billing",
    ]);
    expect(getPrimaryNavigation("SYSTEM_ADMIN").map((item) => item.icon)).toEqual([
      "dashboard",
      "library",
      "briefcase",
      "contract",
      "finance",
    ]);
    expect(ownerShellAcceptance.OWNER_PRIMARY_DESTINATION_COUNT).toBe(5);
  });

  it("lets OFF flags win over the Owner and demo SYSTEM_ADMIN aliases", () => {
    expect(featureAvailability.admin).toBe(false);
    expect(featureAvailability.inputsGoLive).toBe(false);
    expect(featureAvailability.notifications).toBe(false);
    expect(getPrimaryNavigation("SYSTEM_ADMIN")).not.toContainEqual(
      expect.objectContaining({ label: "Admin" }),
    );
    expect(isDisabledTopLevelRoute("/admin")).toBe(true);
    expect(isDisabledTopLevelRoute("/dashboard/inputs-go-live")).toBe(true);
    expect(isDisabledTopLevelRoute("/notifications")).toBe(true);
    expect(isDisabledTopLevelRoute("/construction/exec-1")).toBe(true);
  });

  it("enforces the positive public route allowlist", () => {
    expect(classifyPublicRoute("/home")).toMatchObject({ page: "home", allowed: true });
    expect(classifyPublicRoute("/opportunities/example")).toMatchObject({ page: "opportunities", allowed: true });
    expect(classifyPublicRoute("/contract-mobilization/contracts/example")).toMatchObject({ page: "contract-mobilization", allowed: true });
    expect(classifyPublicRoute("/billing/invoices/example")).toMatchObject({ page: "billing", allowed: true });
    expect(classifyPublicRoute("/master-content/forms")).toMatchObject({ page: "content-library", allowed: true });
    for (const path of [
      "/permits",
      "/engineering",
      "/issues/example",
      "/admin/contracts",
      "/dashboard/inputs-go-live",
      "/unknown-route",
    ]) {
      expect(classifyPublicRoute(path)).toMatchObject({ page: "home", canonicalPath: "/home", allowed: false });
    }
  });
});
