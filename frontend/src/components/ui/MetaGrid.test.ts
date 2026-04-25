import { describe, expect, it } from "vitest";

import { render, screen } from "@testing-library/svelte";

import PanelSectionWrapper from "../layout/PanelSectionTestWrapper.test.svelte";
import MetaGridWrapper from "./MetaGridTestWrapper.test.svelte";

describe("Layout Components", () => {
  it("MetaGrid applies the correct baseline class and renders children", () => {
    const { container } = render(MetaGridWrapper);

    const gridEl = container.querySelector(".meta-grid");
    expect(gridEl).toBeInTheDocument();
    expect(screen.getByTestId("test-child")).toBeInTheDocument();
  });

  it("MetaGrid merges custom classes", () => {
    const { container } = render(MetaGridWrapper, {
      class: "custom-class-123",
    });
    const gridEl = container.querySelector(".meta-grid");
    expect(gridEl).toHaveClass("custom-class-123");
  });

  it("PanelSection applies the correct baseline class and renders children", () => {
    const { container } = render(PanelSectionWrapper);

    const sectionEl = container.querySelector(".panel-section");
    expect(sectionEl).toBeInTheDocument();
    expect(screen.getByTestId("test-child")).toBeInTheDocument();
  });

  it("PanelSection merges custom classes", () => {
    const { container } = render(PanelSectionWrapper, {
      class: "custom-section-class",
    });
    const sectionEl = container.querySelector(".panel-section");
    expect(sectionEl).toHaveClass("custom-section-class");
  });
});
