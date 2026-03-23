import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render } from "@testing-library/svelte";
import Toaster from "./Toaster.svelte";

interface ToasterComponent {
  showSyncingToast(): string;
  showSuccessToast(message: string): string;
  showErrorToast(message: string): string;
  dismissToast(id: string): void;
  dismissAll(): void;
}

describe("Toaster.svelte", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders empty container initially", () => {
    const { container } = render(Toaster);
    const toastContainer = container.querySelector("#toast-container");
    expect(toastContainer).toBeTruthy();
    expect(toastContainer?.children.length).toBe(0);
  });

  it("showSyncingToast returns a toast ID", () => {
    const { component } = render(Toaster);
    const toaster = component as unknown as ToasterComponent;
    const toastId = toaster.showSyncingToast();
    expect(toastId).toBeTruthy();
    expect(typeof toastId).toBe("string");
  });

  it("showSuccessToast returns a toast ID", () => {
    const { component } = render(Toaster);
    const toaster = component as unknown as ToasterComponent;
    const toastId = toaster.showSuccessToast("Test");
    expect(toastId).toBeTruthy();
    expect(typeof toastId).toBe("string");
  });

  it("showErrorToast returns a toast ID", () => {
    const { component } = render(Toaster);
    const toaster = component as unknown as ToasterComponent;
    const toastId = toaster.showErrorToast("Test");
    expect(toastId).toBeTruthy();
    expect(typeof toastId).toBe("string");
  });

  it("dismissToast does not throw", () => {
    const { component } = render(Toaster);
    const toaster = component as unknown as ToasterComponent;
    const toastId = toaster.showSuccessToast("Test");
    expect(() => toaster.dismissToast(toastId)).not.toThrow();
  });

  it("dismissAll does not throw", () => {
    const { component } = render(Toaster);
    const toaster = component as unknown as ToasterComponent;
    toaster.showSuccessToast("Test");
    expect(() => toaster.dismissAll()).not.toThrow();
  });
});
