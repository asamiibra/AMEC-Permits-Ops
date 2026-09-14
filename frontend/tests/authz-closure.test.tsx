import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import App from "../src/App";
import { isSupportedShellRole, personaForRole } from "../src/featureAvailability";

const apiMock = vi.hoisted(() => vi.fn());

vi.mock("../src/api", () => ({
  api: apiMock,
  ApiError: class ApiError extends Error {
    status = 0;
  },
}));
vi.mock("../src/auth", () => ({
  browserAuthMode: () => "ENTRA",
  getSignedInAccountIdentity: vi.fn(async () => ({ displayName: "Mapped User", preferredUsername: "mapped@example.invalid" })),
  signOut: vi.fn(async () => undefined),
}));

const session = (role: string) => ({
  authenticated: true,
  identity: {
    user_id: "user-1",
    tenant_id: "tenant-1",
    object_id: "object-1",
    display_name: "Mapped User",
    preferred_username: "mapped@example.invalid",
    role,
  },
});

describe("AMEC System authorization closure", () => {
  it("maps only the four supported application roles", () => {
    expect(personaForRole("OWNER_SPONSOR")).toBe("OWNER");
    expect(personaForRole("PROCESS_CHAMPION")).toBe("BUSINESS_DEVELOPMENT");
    expect(personaForRole("RESPONSIBLE_ENGINEER")).toBe("ENGINEERING");
    expect(personaForRole("SYSTEM_ADMIN")).toBe("SYSTEM_ADMIN_TECHNICAL");
    expect(personaForRole("REQUIREMENT_STEWARD")).toBeNull();
    expect(personaForRole("garbage")).toBeNull();
    expect(isSupportedShellRole("garbage")).toBe(false);
  });

  it("does not render a business shell for an unsupported valid role", async () => {
    apiMock.mockResolvedValue(session("REQUIREMENT_STEWARD"));
    window.history.replaceState({}, "", "/home");
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Role not enabled for this release" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "Home" })).toBeNull();
    expect(screen.queryByText("Work across the active ProposalOps modules.")).toBeNull();
  });

  it("fails closed when the session request is unavailable", async () => {
    apiMock.mockRejectedValue(new Error("network timeout"));
    window.history.replaceState({}, "", "/home");
    render(<App />);

    await waitFor(() => expect(apiMock).toHaveBeenCalledWith("/api/auth/session"));
    expect(await screen.findByRole("heading", { name: "AMEC System is temporarily unavailable" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "Home" })).toBeNull();
  });
});
