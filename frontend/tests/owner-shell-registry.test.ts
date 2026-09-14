import { describe, expect, it } from "vitest";
import {
  featureAvailability,
  getPrimaryNavigation,
  isDisabledTopLevelRoute,
  ownerShellAcceptance,
} from "../src/featureAvailability";

describe("Owner shell feature registry", () => {
  it("keeps exactly four active modules and Home", () => {
    expect(Object.values(featureAvailability).filter(Boolean)).toHaveLength(4);
    expect(getPrimaryNavigation("SYSTEM_ADMIN").map((item) => item.label)).toEqual([
      "Home",
      "Opportunity / Proposal / Client Tender",
      "Contract / Mobilization",
      "Billing / Invoice / Receivables / Collection",
      "Content Library",
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
});