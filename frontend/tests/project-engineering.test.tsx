import { describe, expect, it } from "vitest";
import { parseD3SyntheticProjectIds } from "../src/ProjectEngineering";

describe("AI-D3 project gate", () => {
  it("recognizes only configured synthetic project IDs", () => {
    const configured = parseD3SyntheticProjectIds(
      "30fed4a2-f044-4de5-ac11-341aa8eef222, 48b36acd-21d3-45e7-83c3-7b17dd4b83af",
    );

    expect(configured.has("30fed4a2-f044-4de5-ac11-341aa8eef222")).toBe(true);
    expect(configured.has("48b36acd-21d3-45e7-83c3-7b17dd4b83af")).toBe(true);
    expect(configured.has("bd0e2006-5e81-4fd2-9f29-b98f2f04e14c")).toBe(false);
  });
});
