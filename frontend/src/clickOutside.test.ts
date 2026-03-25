import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { clickOutside } from "./clickOutside";

describe("clickOutside", () => {
  let container: HTMLElement;
  let targetElement: HTMLElement;
  let callback: () => void;

  beforeEach(() => {
    // Create a container to simulate the document body
    container = document.createElement("div");
    document.body.appendChild(container);

    // Create the target element (the panel)
    targetElement = document.createElement("div");
    targetElement.id = "panel";
    container.appendChild(targetElement);

    // Create callback mock
    callback = vi.fn();
  });

  afterEach(() => {
    document.body.removeChild(container);
    vi.clearAllMocks();
  });

  it("should call callback when clicking outside the element", () => {
    const action = clickOutside(targetElement, { callback });

    // Click outside the panel
    const outsideElement = document.createElement("div");
    container.appendChild(outsideElement);
    outsideElement.click();

    expect(callback).toHaveBeenCalledTimes(1);

    action.destroy();
  });

  it("should NOT call callback when clicking inside the element", () => {
    const action = clickOutside(targetElement, { callback });

    // Click inside the panel
    const insideElement = document.createElement("div");
    targetElement.appendChild(insideElement);
    insideElement.click();

    expect(callback).not.toHaveBeenCalled();

    action.destroy();
  });

  it("should NOT call callback when clicking on ignored selectors", () => {
    const action = clickOutside(targetElement, {
      callback,
      ignoreSelectors: [".node", "header"],
    });

    // Create elements with ignored selectors
    const nodeElement = document.createElement("div");
    nodeElement.className = "node";
    container.appendChild(nodeElement);

    const headerElement = document.createElement("header");
    container.appendChild(headerElement);

    // Click on ignored elements
    nodeElement.click();
    headerElement.click();

    expect(callback).not.toHaveBeenCalled();

    action.destroy();
  });

  it("should NOT call callback when clicking on child of ignored selector", () => {
    const action = clickOutside(targetElement, {
      callback,
      ignoreSelectors: [".node"],
    });

    // Create parent with ignored selector
    const nodeElement = document.createElement("div");
    nodeElement.className = "node";
    container.appendChild(nodeElement);

    // Create child element
    const childElement = document.createElement("span");
    nodeElement.appendChild(childElement);

    // Click on child of ignored element
    childElement.click();

    expect(callback).not.toHaveBeenCalled();

    action.destroy();
  });

  it("should update params when update is called", () => {
    const action = clickOutside(targetElement, {
      callback,
      ignoreSelectors: [".node"],
    });

    // Create elements
    const nodeElement = document.createElement("div");
    nodeElement.className = "node";
    container.appendChild(nodeElement);

    const outsideElement = document.createElement("div");
    container.appendChild(outsideElement);

    // Click on ignored element - should not trigger
    nodeElement.click();
    expect(callback).not.toHaveBeenCalled();

    // Update params to remove ignoreSelectors
    action.update({ callback, ignoreSelectors: [] });

    // Now clicking on node should trigger callback
    nodeElement.click();
    expect(callback).toHaveBeenCalledTimes(1);

    action.destroy();
  });

  it("should remove event listener when destroy is called", () => {
    const action = clickOutside(targetElement, { callback });

    const outsideElement = document.createElement("div");
    container.appendChild(outsideElement);

    // Click should trigger callback
    outsideElement.click();
    expect(callback).toHaveBeenCalledTimes(1);

    // Destroy the action
    action.destroy();

    // Click should no longer trigger callback
    outsideElement.click();
    expect(callback).toHaveBeenCalledTimes(1); // Still 1, not 2
  });

  it("should handle multiple ignore selectors", () => {
    const action = clickOutside(targetElement, {
      callback,
      ignoreSelectors: [".node", "header", ".modal-overlay", ".toast"],
    });

    // Create elements with different ignored selectors
    const nodeElement = document.createElement("div");
    nodeElement.className = "node";
    container.appendChild(nodeElement);

    const headerElement = document.createElement("header");
    container.appendChild(headerElement);

    const modalElement = document.createElement("div");
    modalElement.className = "modal-overlay";
    container.appendChild(modalElement);

    const toastElement = document.createElement("div");
    toastElement.className = "toast";
    container.appendChild(toastElement);

    // Click on all ignored elements
    nodeElement.click();
    headerElement.click();
    modalElement.click();
    toastElement.click();

    expect(callback).not.toHaveBeenCalled();

    action.destroy();
  });

  it("should call callback when clicking on non-ignored element outside panel", () => {
    const action = clickOutside(targetElement, {
      callback,
      ignoreSelectors: [".node"],
    });

    // Create non-ignored element
    const regularElement = document.createElement("div");
    regularElement.className = "regular";
    container.appendChild(regularElement);

    // Click on non-ignored element
    regularElement.click();

    expect(callback).toHaveBeenCalledTimes(1);

    action.destroy();
  });
});
