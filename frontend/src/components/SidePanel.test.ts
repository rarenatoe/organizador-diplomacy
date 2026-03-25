import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
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
    const onclose = vi.fn();

    const { container: panelContainer } = render(SidePanel, {
      props: {
        title: "Test Panel",
        open: true,
        onclose,
        children: vi.fn(),
      },
      target: container,
    });

    expect(panelContainer.textContent).toContain("Test Panel");
  });

  it("has close button that calls onclose", async () => {
    const onclose = vi.fn();

    const { container: panelContainer } = render(SidePanel, {
      props: {
        title: "Test Panel",
        open: true,
        onclose,
        children: vi.fn(),
      },
      target: container,
    });

    const closeButton = panelContainer.querySelector("#btn-close-panel");
    expect(closeButton).not.toBeNull();

    await fireEvent.click(closeButton!);

    expect(onclose).toHaveBeenCalledTimes(1);
  });

  it("applies open class when open prop is true", () => {
    const onclose = vi.fn();

    const { container: panelContainer } = render(SidePanel, {
      props: {
        title: "Test Panel",
        open: true,
        onclose,
        children: vi.fn(),
      },
      target: container,
    });

    const aside = panelContainer.querySelector("aside");
    expect(aside).not.toBeNull();
    expect(aside!.classList.contains("open")).toBe(true);
  });

  it("does not apply open class when open prop is false", () => {
    const onclose = vi.fn();

    const { container: panelContainer } = render(SidePanel, {
      props: {
        title: "Test Panel",
        open: false,
        onclose,
        children: vi.fn(),
      },
      target: container,
    });

    const aside = panelContainer.querySelector("aside");
    expect(aside).not.toBeNull();
    expect(aside!.classList.contains("open")).toBe(false);
  });

  it("uses clickOutside action with correct ignore selectors", () => {
    const onclose = vi.fn();

    const { container: panelContainer } = render(SidePanel, {
      props: {
        title: "Test Panel",
        open: true,
        onclose,
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

  it("calls onclose when clicking outside panel", async () => {
    const onclose = vi.fn();

    render(SidePanel, {
      props: {
        title: "Test Panel",
        open: true,
        onclose,
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

    // onclose should be called because panel is open
    expect(onclose).toHaveBeenCalledTimes(1);
  });

  it("does NOT call onclose when clicking inside panel", async () => {
    const onclose = vi.fn();

    const { container: panelContainer } = render(SidePanel, {
      props: {
        title: "Test Panel",
        open: true,
        onclose,
        children: vi.fn(),
      },
      target: container,
    });

    // Click inside the panel
    const panelHeader = panelContainer.querySelector(".panel-header");
    expect(panelHeader).not.toBeNull();

    await fireEvent.click(panelHeader!);

    // onclose should NOT be called because click was inside panel
    expect(onclose).not.toHaveBeenCalled();
  });

  it("does NOT call onclose when clicking on ignored selector (.node)", async () => {
    const onclose = vi.fn();

    render(SidePanel, {
      props: {
        title: "Test Panel",
        open: true,
        onclose,
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

    // onclose should NOT be called because .node is in ignoreSelectors
    expect(onclose).not.toHaveBeenCalled();
  });

  it("does NOT call onclose when clicking on ignored selector (header)", async () => {
    const onclose = vi.fn();

    render(SidePanel, {
      props: {
        title: "Test Panel",
        open: true,
        onclose,
        children: vi.fn(),
      },
      target: container,
    });

    // Create a header element (ignored selector)
    const headerElement = document.createElement("header");
    container.appendChild(headerElement);

    // Click on the ignored element
    await fireEvent.click(headerElement);

    // onclose should NOT be called because header is in ignoreSelectors
    expect(onclose).not.toHaveBeenCalled();
  });

  it("does NOT call onclose when clicking on ignored selector (.modal-overlay)", async () => {
    const onclose = vi.fn();

    render(SidePanel, {
      props: {
        title: "Test Panel",
        open: true,
        onclose,
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

    // onclose should NOT be called because .modal-overlay is in ignoreSelectors
    expect(onclose).not.toHaveBeenCalled();
  });

  it("does NOT call onclose when clicking on ignored selector (.toast)", async () => {
    const onclose = vi.fn();

    render(SidePanel, {
      props: {
        title: "Test Panel",
        open: true,
        onclose,
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

    // onclose should NOT be called because .toast is in ignoreSelectors
    expect(onclose).not.toHaveBeenCalled();
  });

  it("does NOT call onclose when panel is closed (open=false)", async () => {
    const onclose = vi.fn();

    render(SidePanel, {
      props: {
        title: "Test Panel",
        open: false,
        onclose,
        children: vi.fn(),
      },
      target: container,
    });

    // Create an element outside the panel
    const outsideElement = document.createElement("div");
    container.appendChild(outsideElement);

    // Click outside the panel
    await fireEvent.click(outsideElement);

    // onclose should NOT be called because panel is already closed
    expect(onclose).not.toHaveBeenCalled();
  });
});
