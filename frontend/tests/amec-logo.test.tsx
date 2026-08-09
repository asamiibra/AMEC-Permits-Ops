import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { AmecLogo } from "../src/AmecLogo";

describe("official AMEC logo component", () => {
  it("uses the supplied full composition with responsive high-DPI sources", () => {
    render(<AmecLogo size="md" />);
    const logo = screen.getByRole("img", { name: "AMEC — Art Mark Engineering Consultant" });
    expect(logo).toHaveAttribute("src", "/brand/amec-logo@2x.png");
    expect(logo).toHaveAttribute("srcset", expect.stringContaining("amec-logo@3x.png 3x"));
    expect(logo).toHaveAttribute("width", "600");
    expect(logo).toHaveAttribute("height", "285");
    expect(document.querySelector(".amec-logo-frame")).toBeTruthy();
  });
});
