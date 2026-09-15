import { describe, expect, it } from "vitest";
import {
  featureAvailability,
  getPrimaryNavigation,
  isDisabledTopLevelRoute,
  ownerShellAcceptance,
} from "../src/featureAvailability";
import { classifyPublicRoute } from "../src/domainOwnershipRoutes";

describe("Owner shell feature registry", () => {
  it("keeps the active business modules and Home", () => {
    expect(Object.values(featureAvailability).filter(Boolean)).toHaveLength(12);
    expect(getPrimaryNavigation("SYSTEM_ADMIN").map((item) => item.label)).toEqual(expect.arrayContaining([
      "Home", "My Work", "Opportunities & Proposals", "Contracts & Mobilization", "Billing & Receivables", "Content Library",
      "Design & Engineering", "Regulatory & Submissions", "Engineers Committee", "Construction", "Completion & As-Built", "Handover & Closeout", "Administration",
    ]));
    expect(ownerShellAcceptance.OWNER_PRIMARY_DESTINATION_COUNT).toBe(13);
  });

  it("lets OFF flags win over the Owner and demo SYSTEM_ADMIN aliases", () => {
    expect(featureAvailability.admin).toBe(false);
    expect(featureAvailability.inputsGoLive).toBe(false);
    expect(featureAvailability.notifications).toBe(false);
    expect(getPrimaryNavigation("SYSTEM_ADMIN")).not.toContainEqual(
      expect.objectContaining({ label: "Admin" }),
    );
    expect(isDisabledTopLevelRoute("/admin")).toBe(false);
    expect(isDisabledTopLevelRoute("/dashboard/inputs-go-live")).toBe(true);
    expect(isDisabledTopLevelRoute("/notifications")).toBe(true);
    expect(isDisabledTopLevelRoute("/construction/exec-1")).toBe(false);
  });

  it("enforces the positive public route allowlist", () => {
    expect(classifyPublicRoute("/home")).toMatchObject({ page: "home", allowed: true });
    expect(classifyPublicRoute("/opportunities/example")).toMatchObject({ page: "opportunities", allowed: true });
    expect(classifyPublicRoute("/contract-mobilization/contracts/example")).toMatchObject({ page: "contract-mobilization", allowed: true });
    expect(classifyPublicRoute("/billing/invoices/example")).toMatchObject({ page: "billing", allowed: true });
    expect(classifyPublicRoute("/master-content/forms")).toMatchObject({ page: "content-library", allowed: true });
    expect(classifyPublicRoute("/admin")).toMatchObject({ page: "administration", allowed: true });
    for (const path of [
      "/permits",
      "/issues/example",
      "/dashboard/inputs-go-live",
      "/unknown-route",
    ]) {
      expect(classifyPublicRoute(path)).toMatchObject({ page: "home", canonicalPath: "/home", allowed: false });
    }
  });

  it("redirects legacy Contract records to the same canonical workspace", () => {
    expect(classifyPublicRoute("/admin/contracts/example")).toMatchObject({ page: "contract-mobilization", canonicalPath: "/contract-mobilization/contracts/example", allowed: true });
  });
});
