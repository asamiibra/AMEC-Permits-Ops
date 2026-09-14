import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import App, { userInitials } from "../src/App";

const apiMock = vi.hoisted(() => vi.fn(async () => ({
  authenticated: true,
  auth_mode: "ENTRA",
  identity: {
    user_id: "user-1",
    tenant_id: "tenant-1",
    object_id: "object-1",
    display_name: "Synthetic Owner",
    preferred_username: "owner@example.invalid",
    role: "OWNER_SPONSOR",
  },
})));

vi.mock("../src/api", () => ({ api: apiMock }));
vi.mock("../src/auth", () => ({
  browserAuthMode: () => "ENTRA",
  signOut: vi.fn(async () => undefined),
}));

describe("authenticated account identity", () => {
  it("derives initials without a hardcoded person", () => {
    expect(userInitials("Synthetic Owner", "owner@example.invalid")).toBe("SO");
    expect(userInitials(null, "owner@example.invalid")).toBe("OW");
    expect(userInitials(null, null)).toBe("•");
  });

  it("renders the safe server identity and application role", async () => {
    window.history.replaceState({}, "", "/home");
    render(<App />);

    await waitFor(() => expect(apiMock).toHaveBeenCalledWith("/api/auth/session"));
    const account = await screen.findByRole("button", { name: "Account: Synthetic Owner" });
    expect(account).toHaveTextContent("SO");
    fireEvent.click(account);

    expect(screen.getByText("Synthetic Owner")).toBeVisible();
    expect(screen.getByText("owner@example.invalid")).toBeVisible();
    expect(screen.getByText("Microsoft Entra ID")).toBeVisible();
    expect(screen.getByText("Owner Sponsor")).toBeVisible();
    expect(screen.queryByText("SA", { exact: true })).toBeNull();
    expect(screen.queryByLabelText("Demo as")).toBeNull();
  });
});
