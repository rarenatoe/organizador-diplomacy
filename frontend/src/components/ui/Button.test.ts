import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";
import ButtonTestWrapper, {
  resetClickCount,
  getClickCount,
} from "./ButtonTestWrapper.test.svelte";

describe("Button.svelte", () => {
  beforeEach(() => {
    // eslint-disable-next-line @typescript-eslint/no-unsafe-call
    resetClickCount();
  });

  describe("Rendering and Content", () => {
    it("renders button with text content", () => {
      render(ButtonTestWrapper, {
        props: {
          text: "Click me",
        },
      });

      const button = screen.getByText("Click me");
      expect(button).toBeInTheDocument();
    });

    it("renders button with complex content", () => {
      render(ButtonTestWrapper, {
        props: {
          text: "Save Changes",
        },
      });

      expect(screen.getByText("Save Changes")).toBeInTheDocument();
    });
  });

  describe("Variants", () => {
    it("applies primary variant class", () => {
      render(ButtonTestWrapper, {
        props: {
          variant: "primary",
          text: "Primary Button",
        },
      });

      const button = screen.getByRole("button");
      expect(button).toHaveClass("btn");
      expect(button).toHaveClass("btn-primary");
    });

    it("applies secondary variant class (default)", () => {
      render(ButtonTestWrapper, {
        props: {
          text: "Secondary Button",
        },
      });

      const button = screen.getByRole("button");
      expect(button).toHaveClass("btn");
      expect(button).toHaveClass("btn-secondary");
    });

    it("applies warning variant class", () => {
      render(ButtonTestWrapper, {
        props: {
          variant: "warning",
          text: "Warning Button",
        },
      });

      const button = screen.getByRole("button");
      expect(button).toHaveClass("btn");
      expect(button).toHaveClass("btn-warning");
    });
  });

  describe("Layout", () => {
    it("does not apply flex-fill class by default", () => {
      render(ButtonTestWrapper, {
        props: {
          text: "Normal Button",
        },
      });

      const button = screen.getByRole("button");
      expect(button).not.toHaveClass("flex-fill");
    });

    it("applies flex-fill class when fill is true", () => {
      render(ButtonTestWrapper, {
        props: {
          fill: true,
          text: "Fill Button",
        },
      });

      const button = screen.getByRole("button");
      expect(button).toHaveClass("flex-fill");
      expect(button).toHaveClass("btn");
    });

    it("applies custom className", () => {
      render(ButtonTestWrapper, {
        props: {
          class: "custom-class another-class",
          text: "Custom Button",
        },
      });

      const button = screen.getByRole("button");
      expect(button).toHaveClass("custom-class");
      expect(button).toHaveClass("another-class");
      expect(button).toHaveClass("btn");
    });

    it("applies inline styles", () => {
      render(ButtonTestWrapper, {
        props: {
          style: "background: red; padding: 10px;",
          text: "Styled Button",
        },
      });

      const button = screen.getByRole("button");
      expect(button).toHaveAttribute(
        "style",
        "background: red; padding: 10px;",
      );
    });
  });

  describe("Icon", () => {
    it("does not render icon span when icon is not provided", () => {
      render(ButtonTestWrapper, {
        props: {
          text: "No Icon",
        },
      });

      const button = screen.getByRole("button");
      const spans = button.querySelectorAll("span");
      // Only one span for text content
      expect(spans).toHaveLength(1);
    });

    it("renders icon in separate span when icon is provided", () => {
      render(ButtonTestWrapper, {
        props: {
          icon: "✏️",
          text: "Edit",
        },
      });

      const button = screen.getByRole("button");
      const spans = button.querySelectorAll("span");
      // Two spans: one for icon, one for text
      expect(spans).toHaveLength(2);
      expect(spans[0]).toHaveTextContent("✏️");
      expect(spans[1]).toHaveTextContent("Edit");
    });

    it("renders only icon when provided without affecting text content", () => {
      render(ButtonTestWrapper, {
        props: {
          icon: "➕",
          text: "Add Player",
        },
      });

      const button = screen.getByRole("button");
      // Verify icon is rendered
      expect(button.textContent).toContain("➕");
      expect(screen.getByText("Add Player")).toBeInTheDocument();
    });
  });

  describe("Event Handling", () => {
    it("triggers onclick callback when button is clicked", async () => {
      // Use a component-level test for event handling
      render(ButtonTestWrapper, {
        props: {
          text: "Click Test",
        },
      });

      const button = screen.getByRole("button");
      await fireEvent.click(button);

      // eslint-disable-next-line @typescript-eslint/no-unsafe-call
      expect(getClickCount()).toBe(1);
    });

    it("does not error when onclick is not provided", async () => {
      render(ButtonTestWrapper, {
        props: {
          text: "No Handler",
          noHandler: true,
        },
      });

      const button = screen.getByRole("button");
      // Should not throw error
      await fireEvent.click(button);
      expect(button).toBeInTheDocument();
    });
  });

  describe("Disabled State", () => {
    it("does not have disabled attribute by default", () => {
      render(ButtonTestWrapper, {
        props: {
          text: "Enabled Button",
        },
      });

      const button = screen.getByRole("button");
      expect(button).not.toBeDisabled();
    });

    it("applies disabled attribute when disabled is true", () => {
      render(ButtonTestWrapper, {
        props: {
          disabled: true,
          text: "Disabled Button",
        },
      });

      const button = screen.getByRole("button");
      expect(button).toBeDisabled();
      expect(button).toHaveAttribute("disabled");
    });

    it("does not trigger onclick when disabled and clicked", async () => {
      render(ButtonTestWrapper, {
        props: {
          disabled: true,
          text: "Disabled Click Test",
        },
      });

      const button = screen.getByRole("button");
      expect(button).toBeDisabled();
      await fireEvent.click(button);

      // Click event should not trigger handler on disabled button
      // eslint-disable-next-line @typescript-eslint/no-unsafe-call
      expect(getClickCount()).toBe(0);
    });

    it("shows title on hover even when not disabled", () => {
      render(ButtonTestWrapper, {
        props: {
          title: "This will save your changes",
          text: "Save",
        },
      });

      const button = screen.getByRole("button");
      expect(button).toHaveAttribute("title", "This will save your changes");
    });
  });

  describe("Combined Props", () => {
    it("applies multiple props correctly", () => {
      render(ButtonTestWrapper, {
        props: {
          variant: "primary",
          fill: true,
          icon: "✨",
          class: "extra-class",
          style: "margin: 5px;",
          title: "Combined test",
          text: "Combined Props",
        },
      });

      const button = screen.getByRole("button");

      // Check classes
      expect(button).toHaveClass("btn");
      expect(button).toHaveClass("btn-primary");
      expect(button).toHaveClass("flex-fill");
      expect(button).toHaveClass("extra-class");

      // Check attributes
      expect(button).toHaveAttribute("style", "margin: 5px;");
      expect(button).toHaveAttribute("title", "Combined test");

      // Check icon and text
      const spans = button.querySelectorAll("span");
      expect(spans).toHaveLength(2);
      expect(spans[0]).toHaveTextContent("✨");
      expect(spans[1]).toHaveTextContent("Combined Props");

      // Check disabled state (should be enabled)
      expect(button).not.toBeDisabled();
    });

    it("works with all props including disabled", async () => {
      render(ButtonTestWrapper, {
        props: {
          variant: "warning",
          fill: true,
          disabled: true,
          icon: "🗑️",
          title: "Cannot delete at this time",
          text: "Delete",
        },
      });

      const button = screen.getByRole("button");

      expect(button).toBeDisabled();
      expect(button).toHaveClass("btn-warning");
      expect(button).toHaveClass("flex-fill");
      expect(button).toHaveAttribute("title", "Cannot delete at this time");

      // Verify onclick doesn't fire
      await fireEvent.click(button);
      // eslint-disable-next-line @typescript-eslint/no-unsafe-call
      expect(getClickCount()).toBe(0);
    });
  });
});
