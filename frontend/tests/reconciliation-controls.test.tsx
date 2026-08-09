import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ReconciliationControls } from "../src/ReconciliationControls";

describe("Weeks 1–8 control evidence", () => {
  it("renders blocked and stale package controls", () => {
    render(<ReconciliationControls state={{ packageStatus: "BLOCKED", blockedReasons: ["Missing approved title deed"], packageStale: true, revisionStale: true, currentRevision: false, evidenceLabel: "title deed evidence" }} />);
    expect(screen.getByText("Missing approved title deed")).toBeInTheDocument();
    expect(screen.getByText(/STALE PACKAGE/)).toBeInTheDocument();
    expect(screen.getByText(/STALE PREPARATION REVISION/)).toBeInTheDocument();
    expect(screen.getByText("Historical revision")).toBeInTheDocument();
  });

  it("renders assisted municipality mappings, mismatch, findings and notification failure", () => {
    render(<ReconciliationControls state={{ packageStatus: "READY", municipalityValue: "Doha", dropdownCode: "MUN_A", dropdownLabel: "Doha Municipality", portalMismatch: true, findingOwner: "Responsible Engineer", taskLabel: "Review drawing", notificationStatus: "FAILED", precheckRun: "PRECHECK-01", precheckRevision: "REV-01", handoffStatus: "HUMAN SUBMISSION REQUIRED" }} />);
    expect(screen.getByText(/READY — eligible/)).toBeInTheDocument();
    expect(screen.getByText(/Doha Municipality/)).toBeInTheDocument();
    expect(screen.getByText(/PORTAL MISMATCH/)).toBeInTheDocument();
    expect(screen.getByText(/Notification FAILED/)).toBeInTheDocument();
    expect(screen.getByText("Responsible Engineer")).toBeInTheDocument();
    expect(screen.getByText(/PRECHECK-01/)).toBeInTheDocument();
    expect(screen.getByText(/HUMAN SUBMISSION REQUIRED/)).toBeInTheDocument();
    expect(screen.getByTestId("no-final-submit")).toBeInTheDocument();
  });

  it("renders Arabic RTL while keeping mixed identifiers readable", () => {
    render(<ReconciliationControls state={{ rtl: true, findingOwner: "مسؤول هندسي", precheckRun: "PRECHECK-AR-01" }} />);
    expect(screen.getByRole("region")).toHaveAttribute("dir", "rtl");
    expect(screen.getByText("GHCE-2026-0142")).toHaveAttribute("dir", "ltr");
  });
});
