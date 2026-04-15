import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";
import { tick } from "svelte";
import Tooltip from "./Tooltip.svelte";

describe("Tooltip.svelte", () => {
  it("renders as info icon", () => {
    render(Tooltip, { props: { text: "Test tooltip", icon: "ℹ️" } });
    const infoIcon = screen.getByText("ℹ️");
    expect(infoIcon).toBeInTheDocument();
    expect(infoIcon).toHaveClass("info-icon");
  });

  it("uses custom icon when provided", () => {
    render(Tooltip, { props: { text: "Test", icon: "❓" } });
    expect(screen.getByText("❓")).toBeInTheDocument();
  });

  it("renders text content in tooltip popover on hover", async () => {
    const { container } = render(Tooltip, {
      props: { text: "This is a tooltip", icon: "ℹ️" },
    });

    // Tooltip should not be in DOM initially
    expect(document.body.querySelector(".tooltip-popover")).toBeNull();

    // Trigger hover
    const trigger = container.querySelector(".tooltip-trigger")!;
    await fireEvent.mouseEnter(trigger);
    await tick();

    const tooltipPopover = document.body.querySelector(".tooltip-popover");
    expect(tooltipPopover).toBeInTheDocument();
    expect(tooltipPopover).toHaveTextContent("This is a tooltip");
  });

  it("has correct tooltip structure", () => {
    const { container } = render(Tooltip, {
      props: { text: "Test", icon: "ℹ️" },
    });
    const tooltip = container.querySelector(".tooltip-trigger");
    expect(tooltip).toBeInTheDocument();

    const infoIcon = tooltip?.querySelector(".info-icon");
    expect(infoIcon).toBeInTheDocument();
  });

  it("handles empty text gracefully on hover", async () => {
    const { container } = render(Tooltip, { props: { text: "", icon: "ℹ️" } });

    const trigger = container.querySelector(".tooltip-trigger")!;
    await fireEvent.mouseEnter(trigger);
    await tick();

    const tooltipPopover = document.body.querySelector(".tooltip-popover");
    expect(tooltipPopover).toBeInTheDocument();
    expect(tooltipPopover).toHaveTextContent("");
  });

  it("handles special characters in text on hover", async () => {
    const specialText = "Special chars: áéíóú & symbols @#$%";
    const { container } = render(Tooltip, {
      props: { text: specialText, icon: "ℹ️" },
    });

    const trigger = container.querySelector(".tooltip-trigger")!;
    await fireEvent.mouseEnter(trigger);
    await tick();

    const tooltipPopover = document.body.querySelector(".tooltip-popover");
    expect(tooltipPopover).toBeInTheDocument();
    expect(tooltipPopover).toHaveTextContent(specialText);
  });

  it("has correct CSS classes applied", () => {
    const { container } = render(Tooltip, {
      props: { text: "Test", icon: "ℹ️" },
    });
    const tooltip = container.querySelector(".tooltip-trigger");
    expect(tooltip).toHaveClass("tooltip-trigger");
  });
});
