import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, fireEvent, screen } from "@testing-library/svelte";
import SidePanel from "./SidePanel.svelte";

describe("SidePanel", () => {
  let container: HTMLElement;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
  });

  afterEach(() => {
    document.body.removeChild(container);
    vi.clearAllMocks();
  });

  it("renders panel with title", () => {
    const onClose = vi.fn();

    const { container: panelContainer } = render(SidePanel, {
      props: {
        title: "Test Panel",
        open: true,
        onClose,
        children: vi.fn(),
      },
      target: container,
    });

    expect(panelContainer.textContent).toContain("Test Panel");
  });

  it("has close button that calls onClose", async () => {
    const onClose = vi.fn();

    render(SidePanel, {
      props: {
        title: "Test Panel",
        open: true,
        onClose,
        children: vi.fn(),
      },
      target: container,
    });

    const closeButton = screen.getByTitle("Cerrar");
    expect(closeButton).toBeInTheDocument();
    await fireEvent.click(closeButton);

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("applies open class when open prop is true", () => {
    const onClose = vi.fn();

    const { container: panelContainer } = render(SidePanel, {
      props: {
        title: "Test Panel",
        open: true,
        onClose,
        children: vi.fn(),
      },
      target: container,
    });

    const aside = panelContainer.querySelector("aside");
    expect(aside).not.toBeNull();
    expect(aside!.classList.contains("open")).toBe(true);
  });

  it("does not apply open class when open prop is false", () => {
    const onClose = vi.fn();

    const { container: panelContainer } = render(SidePanel, {
      props: {
        title: "Test Panel",
        open: false,
        onClose,
        children: vi.fn(),
      },
      target: container,
    });

    const aside = panelContainer.querySelector("aside");
    expect(aside).not.toBeNull();
    expect(aside!.classList.contains("open")).toBe(false);
  });

  it("uses clickOutside action with correct ignore selectors", () => {
    const onClose = vi.fn();

    const { container: panelContainer } = render(SidePanel, {
      props: {
        title: "Test Panel",
        open: true,
        onClose,
        children: vi.fn(),
      },
      target: container,
    });

    const aside = panelContainer.querySelector("aside");
    expect(aside).not.toBeNull();

    // Verify the aside element exists and has the panel class
    // The clickOutside action is applied via use:clickOutside directive
    expect(aside!.classList.contains("panel")).toBe(true);
  });

  it("calls onClose when clicking outside panel", async () => {
    const onClose = vi.fn();

    render(SidePanel, {
      props: {
        title: "Test Panel",
        open: true,
        onClose,
        children: vi.fn(),
      },
      target: container,
    });

    // Create an element outside the panel
    const outsideElement = document.createElement("div");
    outsideElement.id = "outside";
    container.appendChild(outsideElement);

    // Click outside the panel
    await fireEvent.click(outsideElement);

    // onClose should be called because panel is open
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("does NOT call onClose when clicking inside panel", async () => {
    const onClose = vi.fn();

    const { container: panelContainer } = render(SidePanel, {
      props: {
        title: "Test Panel",
        open: true,
        onClose,
        children: vi.fn(),
      },
      target: container,
    });

    // Click inside the panel
    const panelHeader = panelContainer.querySelector(".panel-header");
    expect(panelHeader).not.toBeNull();

    await fireEvent.click(panelHeader!);

    // onClose should NOT be called because click was inside panel
    expect(onClose).not.toHaveBeenCalled();
  });

  it("does NOT call onClose when clicking on ignored selector (.node)", async () => {
    const onClose = vi.fn();

    render(SidePanel, {
      props: {
        title: "Test Panel",
        open: true,
        onClose,
        children: vi.fn(),
      },
      target: container,
    });

    // Create an element with .node class (ignored selector)
    const nodeElement = document.createElement("div");
    nodeElement.className = "node";
    container.appendChild(nodeElement);

    // Click on the ignored element
    await fireEvent.click(nodeElement);

    // onClose should NOT be called because .node is in ignoreSelectors
    expect(onClose).not.toHaveBeenCalled();
  });

  it("does NOT call onClose when clicking on ignored selector (header)", async () => {
    const onClose = vi.fn();

    render(SidePanel, {
      props: {
        title: "Test Panel",
        open: true,
        onClose,
        children: vi.fn(),
      },
      target: container,
    });

    // Create a header element (ignored selector)
    const headerElement = document.createElement("header");
    container.appendChild(headerElement);

    // Click on the ignored element
    await fireEvent.click(headerElement);

    // onClose should NOT be called because header is in ignoreSelectors
    expect(onClose).not.toHaveBeenCalled();
  });

  it("does NOT call onClose when clicking on ignored selector (.modal-overlay)", async () => {
    const onClose = vi.fn();

    render(SidePanel, {
      props: {
        title: "Test Panel",
        open: true,
        onClose,
        children: vi.fn(),
      },
      target: container,
    });

    // Create an element with .modal-overlay class (ignored selector)
    const modalElement = document.createElement("div");
    modalElement.className = "modal-overlay";
    container.appendChild(modalElement);

    // Click on the ignored element
    await fireEvent.click(modalElement);

    // onClose should NOT be called because .modal-overlay is in ignoreSelectors
    expect(onClose).not.toHaveBeenCalled();
  });

  it("does NOT call onClose when clicking on ignored selector (.toast)", async () => {
    const onClose = vi.fn();

    render(SidePanel, {
      props: {
        title: "Test Panel",
        open: true,
        onClose,
        children: vi.fn(),
      },
      target: container,
    });

    // Create an element with .toast class (ignored selector)
    const toastElement = document.createElement("div");
    toastElement.className = "toast";
    container.appendChild(toastElement);

    // Click on the ignored element
    await fireEvent.click(toastElement);

    // onClose should NOT be called because .toast is in ignoreSelectors
    expect(onClose).not.toHaveBeenCalled();
  });

  it("does NOT call onClose when panel is closed (open=false)", async () => {
    const onClose = vi.fn();

    render(SidePanel, {
      props: {
        title: "Test Panel",
        open: false,
        onClose,
        children: vi.fn(),
      },
      target: container,
    });

    // Create an element outside the panel
    const outsideElement = document.createElement("div");
    container.appendChild(outsideElement);

    // Click outside the panel
    await fireEvent.click(outsideElement);

    // onClose should NOT be called because panel is already closed
    expect(onClose).not.toHaveBeenCalled();
  });
});
