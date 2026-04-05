import { render, screen } from "@testing-library/svelte";
import { describe, it, expect } from "vitest";
import Tooltip from "./Tooltip.svelte";

describe("Tooltip.svelte", () => {
  it("renders the info icon", () => {
    render(Tooltip, { props: { text: "Test tooltip" } });
    const infoIcon = screen.getByText("ℹ️");
    expect(infoIcon).toBeInTheDocument();
    expect(infoIcon).toHaveClass("info-icon");
  });

  it("renders text content in tooltip popover", () => {
    render(Tooltip, { props: { text: "This is a tooltip" } });
    const tooltipPopover = document.querySelector(".tooltip-popover");
    expect(tooltipPopover).toBeInTheDocument();
    expect(tooltipPopover).toHaveTextContent("This is a tooltip");
  });

  it("has correct tooltip structure", () => {
    const { container } = render(Tooltip, { props: { text: "Test" } });
    const tooltip = container.querySelector(".tooltip");
    expect(tooltip).toBeInTheDocument();

    const infoIcon = tooltip?.querySelector(".info-icon");
    expect(infoIcon).toBeInTheDocument();
    expect(infoIcon).toHaveTextContent("ℹ️");

    const popover = tooltip?.querySelector(".tooltip-popover");
    expect(popover).toBeInTheDocument();
    expect(popover).toHaveTextContent("Test");
  });

  it("handles empty text gracefully", () => {
    render(Tooltip, { props: { text: "" } });
    const tooltipPopover = document.querySelector(".tooltip-popover");
    expect(tooltipPopover).toBeInTheDocument();
    expect(tooltipPopover).toHaveTextContent("");
  });

  it("handles special characters in text", () => {
    const specialText = "Special chars: áéíóú & symbols @#$%";
    render(Tooltip, { props: { text: specialText } });
    const tooltipPopover = document.querySelector(".tooltip-popover");
    expect(tooltipPopover).toBeInTheDocument();
    expect(tooltipPopover).toHaveTextContent(specialText);
  });

  it("has correct CSS classes applied", () => {
    const { container } = render(Tooltip, { props: { text: "Test" } });
    const tooltip = container.querySelector(".tooltip");
    expect(tooltip).toHaveClass("tooltip");

    const infoIcon = tooltip?.querySelector(".info-icon");
    expect(infoIcon).toHaveClass("info-icon");

    const popover = tooltip?.querySelector(".tooltip-popover");
    expect(popover).toHaveClass("tooltip-popover");
  });
});
