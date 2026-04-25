import { render, screen } from "@testing-library/svelte";

import MetaItem from "./MetaItem.svelte";

describe("MetaItem", () => {
  it("renders both label and value correctly", () => {
    render(MetaItem, { label: "Test Label", value: "Test Value" });

    // Check Label
    const labelEl = screen.getByText("Test Label");
    expect(labelEl).toBeInTheDocument();
    expect(labelEl).toHaveClass("meta-key");

    // Check Value
    const valueEl = screen.getByText("Test Value");
    expect(valueEl).toBeInTheDocument();
    expect(valueEl).toHaveClass("meta-val");
  });

  it("handles missing/null values gracefully without rendering 'null' strings", () => {
    const { container } = render(MetaItem, {
      label: "Empty Label",
      value: null,
    });

    expect(screen.getByText("Empty Label")).toBeInTheDocument();

    const valSpan = container.querySelector(".meta-val");
    expect(valSpan).toBeInTheDocument();
    expect(valSpan?.textContent.trim()).toBe(""); // Ensures "null" is not printed
  });

  it("renders numerical values properly", () => {
    render(MetaItem, { label: "Intentos", value: 42 });
    expect(screen.getByText("42")).toBeInTheDocument();
  });
});
