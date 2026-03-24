import { describe, it, expect, vi } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
import Header from "./Header.svelte";

describe("Header", () => {
  it("renders header correctly", () => {
    const onnewdraft = vi.fn();

    const { container } = render(Header, {
      props: {
        onnewdraft,
      },
    });

    expect(container.textContent).toContain("Organizador Diplomacy");
  });

  it("shows Nueva Versión button", () => {
    const onnewdraft = vi.fn();

    const { container } = render(Header, {
      props: {
        onnewdraft,
      },
    });

    const newVersionButton = container.querySelector("#btn-new-version");
    expect(newVersionButton).not.toBeNull();
    expect(newVersionButton!.textContent).toContain("Nueva Lista");
  });

  it("clicking Nueva Versión button calls onnewdraft", async () => {
    const onnewdraft = vi.fn();

    const { container } = render(Header, {
      props: {
        onnewdraft,
      },
    });

    const newVersionButton = container.querySelector("#btn-new-version");
    expect(newVersionButton).not.toBeNull();

    await fireEvent.click(newVersionButton!);

    expect(onnewdraft).toHaveBeenCalledTimes(1);
  });

  it("Nueva Versión button uses btn-primary class", () => {
    const onnewdraft = vi.fn();

    const { container } = render(Header, {
      props: {
        onnewdraft,
      },
    });

    const newVersionButton = container.querySelector("#btn-new-version");
    expect(newVersionButton).not.toBeNull();
    expect(newVersionButton!.classList.contains("btn-primary")).toBe(true);
  });
});
