import { describe, expect, it, vi } from "vitest";

import { fireEvent, render } from "@testing-library/svelte";

import Node from "./Node.svelte";

describe("Node", () => {
  const defaultProps = {
    variant: "game" as const,
    nodeId: 1,
    title: "Test Node",
    subtitle: "Test Subtitle",
    icon: "",
    metadata: ["Test metadata 1", "Test metadata 2"],
    onClick: vi.fn(),
  };

  it("renders with game variant", () => {
    const { container } = render(Node, { props: defaultProps });

    expect(container.querySelector(".node-game")).toBeInTheDocument();
    expect(container.querySelector(".node-snapshot")).not.toBeInTheDocument();
  });

  it("renders with snapshot variant", () => {
    const { container } = render(Node, {
      props: { ...defaultProps, variant: "snapshot" },
    });

    expect(container.querySelector(".node-snapshot")).toBeInTheDocument();
    expect(container.querySelector(".node-game")).not.toBeInTheDocument();
  });

  it("applies active class when isActive is true", () => {
    const { container } = render(Node, {
      props: { ...defaultProps, isActive: true },
    });

    expect(container.querySelector(".node.active")).toBeInTheDocument();
  });

  it("does not apply active class when isActive is false", () => {
    const { container } = render(Node, {
      props: { ...defaultProps, isActive: false },
    });

    expect(container.querySelector(".node.active")).not.toBeInTheDocument();
  });

  it("renders correct number of footer items based on metadata", () => {
    const { container } = render(Node, {
      props: {
        ...defaultProps,
        metadata: ["Item 1", "Item 2", "Item 3"],
      },
    });

    const footerItems = container.querySelectorAll(".footer-item");
    expect(footerItems).toHaveLength(3);
  });

  it("renders no footer items when metadata is empty", () => {
    const { container } = render(Node, {
      props: { ...defaultProps, metadata: [] },
    });

    const footerItems = container.querySelectorAll(".footer-item");
    expect(footerItems).toHaveLength(0);
  });

  it("fires onDelete callback when delete button is clicked", async () => {
    const onDelete = vi.fn();
    const { container } = render(Node, {
      props: { ...defaultProps, onDelete },
    });

    const deleteButton = container.querySelector('button[title*="Eliminar"]');
    expect(deleteButton).toBeInTheDocument();
    if (deleteButton) {
      await fireEvent.click(deleteButton);
    }
    expect(onDelete).toHaveBeenCalledTimes(1);
  });

  it("does not render delete button when onDelete is not provided", () => {
    const { container } = render(Node, {
      props: { ...defaultProps, onDelete: undefined },
    });

    const deleteButton = container.querySelector('button[title*="Eliminar"]');
    expect(deleteButton).not.toBeInTheDocument();
  });

  it("fires onClick callback when node is clicked", async () => {
    const onClick = vi.fn();
    const { container } = render(Node, {
      props: { ...defaultProps, onClick },
    });

    const node = container.querySelector(".node");
    expect(node).toBeInTheDocument();
    if (node) {
      await fireEvent.click(node);
    }
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("fires onClick callback when Enter key is pressed", async () => {
    const onClick = vi.fn();
    const { container } = render(Node, {
      props: { ...defaultProps, onClick },
    });

    const node = container.querySelector(".node");
    expect(node).toBeInTheDocument();
    if (node) {
      await fireEvent.keyDown(node, { key: "Enter" });
    }
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("renders title and subtitle correctly", () => {
    const { container } = render(Node, {
      props: defaultProps,
    });

    expect(container.querySelector(".node-label")?.textContent).toBe(
      "Test Node",
    );
    expect(container.querySelector(".node-name")?.textContent).toBe(
      "Test Subtitle",
    );
  });

  it("renders icon correctly", () => {
    const { container } = render(Node, {
      props: { ...defaultProps, icon: "" },
    });

    expect(container.querySelector(".node-icon")?.textContent).toBe("");
  });
});
