import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AuthFailureSurface } from "../src/AuthFailureSurface";

describe("AuthFailureSurface", () => {
  it("presents a safe retry action without exposing startup details", () => {
    const reload = vi.fn();
    vi.stubGlobal("location", { reload });
    render(<AuthFailureSurface />);

    expect(screen.getByRole("alert")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "ProposalOps couldn’t start sign-in" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Retry sign-in" })).toBeTruthy();
    expect(screen.queryByText(/token|tenant|stack|exception/i)).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Retry sign-in" }));
    expect(reload).toHaveBeenCalledOnce();
  });
});
