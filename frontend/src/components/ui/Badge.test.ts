import { describe, expect, it } from "vitest";

import { render, screen } from "@testing-library/svelte";

import Badge from "./Badge.svelte";

describe("Badge.svelte", () => {
  it("renders text correctly", () => {
    render(Badge, { props: { variant: "info", text: "Test Badge" } });
    expect(screen.getByText("Test Badge")).toBeInTheDocument();
  });

  it("applies correct variant classes", () => {
    const { container } = render(Badge, {
      props: { variant: "warning", text: "Warning" },
    });
    const badge = container.querySelector(".badge");
    expect(badge).toHaveClass("warning");
    expect(badge).toHaveClass("badge");
  });

  it("applies info variant class", () => {
    const { container } = render(Badge, {
      props: { variant: "info", text: "Info" },
    });
    const badge = container.querySelector(".badge");
    expect(badge).toHaveClass("info");
  });

  it("applies success variant class", () => {
    const { container } = render(Badge, {
      props: { variant: "success", text: "Success" },
    });
    const badge = container.querySelector(".badge");
    expect(badge).toHaveClass("success");
  });

  it("applies error variant class", () => {
    const { container } = render(Badge, {
      props: { variant: "error", text: "Error" },
    });
    const badge = container.querySelector(".badge");
    expect(badge).toHaveClass("error");
  });

  it("applies pill class when pill prop is true", () => {
    const { container } = render(Badge, {
      props: { variant: "info", text: "Pill Badge", pill: true },
    });
    const badge = container.querySelector(".badge");
    expect(badge).toHaveClass("pill");
  });

  it("does not apply pill class when pill prop is false", () => {
    const { container } = render(Badge, {
      props: { variant: "info", text: "Normal Badge", pill: false },
    });
    const badge = container.querySelector(".badge");
    expect(badge).not.toHaveClass("pill");
  });

  it("does not apply pill class when pill prop is omitted", () => {
    const { container } = render(Badge, {
      props: { variant: "info", text: "Default Badge" },
    });
    const badge = container.querySelector(".badge");
    expect(badge).not.toHaveClass("pill");
  });

  it("applies fixed-width class when fixedWidth prop is true", () => {
    const { container } = render(Badge, {
      props: { variant: "info", text: "Fixed Badge", fixedWidth: true },
    });
    const badge = container.querySelector(".badge");
    expect(badge).toHaveClass("fixed-width");
  });

  it("does not apply fixed-width class when fixedWidth prop is false", () => {
    const { container } = render(Badge, {
      props: { variant: "info", text: "Flexible Badge", fixedWidth: false },
    });
    const badge = container.querySelector(".badge");
    expect(badge).not.toHaveClass("fixed-width");
  });

  it("does not apply fixed-width class when fixedWidth prop is omitted", () => {
    const { container } = render(Badge, {
      props: { variant: "info", text: "Default Badge" },
    });
    const badge = container.querySelector(".badge");
    expect(badge).not.toHaveClass("fixed-width");
  });

  it("applies multiple classes correctly", () => {
    const { container } = render(Badge, {
      props: {
        variant: "warning",
        text: "Multi Badge",
        pill: true,
        fixedWidth: true,
      },
    });
    const badge = container.querySelector(".badge");
    expect(badge).toHaveClass("badge");
    expect(badge).toHaveClass("warning");
    expect(badge).toHaveClass("pill");
    expect(badge).toHaveClass("fixed-width");
  });

  it("applies the subtle class by default", () => {
    const { container } = render(Badge, {
      props: { variant: "info", text: "Test" },
    });
    const badge = container.querySelector(".badge");
    expect(badge?.classList.contains("subtle")).toBe(true);
  });

  it("removes the subtle class when subtle prop is false", () => {
    const { container } = render(Badge, {
      props: { variant: "success", text: "Solid", subtle: false },
    });
    const badge = container.querySelector(".badge");
    expect(badge?.classList.contains("subtle")).toBe(false);
  });
});
