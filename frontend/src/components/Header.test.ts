import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
import Header from "./Header.svelte";
import {
  setSelectedSnapshot,
  deselectSnapshot,
  setSnapshotCount,
  getSelectedSnapshot,
} from "../stores.svelte";

describe("Header", () => {
  beforeEach(() => {
    deselectSnapshot();
    setSnapshotCount(0);
  });

  it("renders header correctly", () => {
    const onrefresh = vi.fn();
    const onsync = vi.fn();
    const onorganizar = vi.fn();

    const { container } = render(Header, {
      props: {
        onrefresh,
        onsync,
        onorganizar,
        syncing: false,
        running: false,
      },
    });

    expect(container.textContent).toContain("Organizador Diplomacy");
  });

  it("does not show clear selection button when no snapshot is selected", () => {
    deselectSnapshot();
    const onrefresh = vi.fn();
    const onsync = vi.fn();
    const onorganizar = vi.fn();

    const { container } = render(Header, {
      props: {
        onrefresh,
        onsync,
        onorganizar,
        syncing: false,
        running: false,
      },
    });

    const clearButton = container.querySelector("#btn-deselect");
    expect(clearButton).toBeNull();
  });

  it("shows clear selection button when snapshot is selected", () => {
    setSelectedSnapshot(42);
    const onrefresh = vi.fn();
    const onsync = vi.fn();
    const onorganizar = vi.fn();

    const { container } = render(Header, {
      props: {
        onrefresh,
        onsync,
        onorganizar,
        syncing: false,
        running: false,
      },
    });

    const clearButton = container.querySelector("#btn-deselect");
    expect(clearButton).not.toBeNull();
    expect(clearButton!.textContent).toContain("Limpiar selección");
  });

  it("clear selection button has correct title", () => {
    setSelectedSnapshot(42);
    const onrefresh = vi.fn();
    const onsync = vi.fn();
    const onorganizar = vi.fn();

    const { container } = render(Header, {
      props: {
        onrefresh,
        onsync,
        onorganizar,
        syncing: false,
        running: false,
      },
    });

    const clearButton = container.querySelector("#btn-deselect");
    expect(clearButton).not.toBeNull();
    expect(clearButton!.getAttribute("title")).toBe(
      "Limpiar la selección actual",
    );
  });

  it("clicking clear selection button deselects snapshot", async () => {
    setSelectedSnapshot(42);
    const onrefresh = vi.fn();
    const onsync = vi.fn();
    const onorganizar = vi.fn();

    const { container } = render(Header, {
      props: {
        onrefresh,
        onsync,
        onorganizar,
        syncing: false,
        running: false,
      },
    });

    const clearButton = container.querySelector("#btn-deselect");
    expect(clearButton).not.toBeNull();

    await fireEvent.click(clearButton!);

    expect(getSelectedSnapshot()).toBeNull();
  });

  it("clear selection button uses btn-secondary class", () => {
    setSelectedSnapshot(42);
    const onrefresh = vi.fn();
    const onsync = vi.fn();
    const onorganizar = vi.fn();

    const { container } = render(Header, {
      props: {
        onrefresh,
        onsync,
        onorganizar,
        syncing: false,
        running: false,
      },
    });

    const clearButton = container.querySelector("#btn-deselect");
    expect(clearButton).not.toBeNull();
    expect(clearButton!.classList.contains("btn-secondary")).toBe(true);
  });

  it("organizar button shows correct label when snapshot is selected", () => {
    setSelectedSnapshot(123);
    const onrefresh = vi.fn();
    const onsync = vi.fn();
    const onorganizar = vi.fn();

    const { container } = render(Header, {
      props: {
        onrefresh,
        onsync,
        onorganizar,
        syncing: false,
        running: false,
      },
    });

    const organizarLabel = container.querySelector("#organizar-label");
    expect(organizarLabel).not.toBeNull();
    expect(organizarLabel!.textContent).toBe("Organizar · #123");
  });

  it("organizar button shows default label when no snapshot is selected", () => {
    deselectSnapshot();
    const onrefresh = vi.fn();
    const onsync = vi.fn();
    const onorganizar = vi.fn();

    const { container } = render(Header, {
      props: {
        onrefresh,
        onsync,
        onorganizar,
        syncing: false,
        running: false,
      },
    });

    const organizarLabel = container.querySelector("#organizar-label");
    expect(organizarLabel).not.toBeNull();
    expect(organizarLabel!.textContent).toBe("Organizar");
  });

  it("organizar button is disabled when no snapshot is selected", () => {
    deselectSnapshot();
    const onrefresh = vi.fn();
    const onsync = vi.fn();
    const onorganizar = vi.fn();

    const { container } = render(Header, {
      props: {
        onrefresh,
        onsync,
        onorganizar,
        syncing: false,
        running: false,
      },
    });

    const organizarButton = container.querySelector("#btn-organizar");
    expect(organizarButton).not.toBeNull();
    expect((organizarButton as HTMLButtonElement).disabled).toBe(true);
  });

  it("organizar button is enabled when snapshot is selected", () => {
    setSelectedSnapshot(42);
    const onrefresh = vi.fn();
    const onsync = vi.fn();
    const onorganizar = vi.fn();

    const { container } = render(Header, {
      props: {
        onrefresh,
        onsync,
        onorganizar,
        syncing: false,
        running: false,
      },
    });

    const organizarButton = container.querySelector("#btn-organizar");
    expect(organizarButton).not.toBeNull();
    expect((organizarButton as HTMLButtonElement).disabled).toBe(false);
  });

  it("buttons are disabled when syncing", () => {
    setSelectedSnapshot(42);
    const onrefresh = vi.fn();
    const onsync = vi.fn();
    const onorganizar = vi.fn();

    const { container } = render(Header, {
      props: {
        onrefresh,
        onsync,
        onorganizar,
        syncing: true,
        running: false,
      },
    });

    const refreshButton = container.querySelector("#btn-refresh");
    const syncButton = container.querySelector("#btn-sync");
    const organizarButton = container.querySelector("#btn-organizar");

    expect(refreshButton).not.toBeNull();
    expect(syncButton).not.toBeNull();
    expect(organizarButton).not.toBeNull();

    // Note: refresh button is not disabled by syncing state in the current implementation
    expect((syncButton as HTMLButtonElement).disabled).toBe(true);
    expect((organizarButton as HTMLButtonElement).disabled).toBe(true);
  });

  it("buttons are disabled when running", () => {
    setSelectedSnapshot(42);
    const onrefresh = vi.fn();
    const onsync = vi.fn();
    const onorganizar = vi.fn();

    const { container } = render(Header, {
      props: {
        onrefresh,
        onsync,
        onorganizar,
        syncing: false,
        running: true,
      },
    });

    const syncButton = container.querySelector("#btn-sync");
    const organizarButton = container.querySelector("#btn-organizar");

    expect(syncButton).not.toBeNull();
    expect(organizarButton).not.toBeNull();

    expect((syncButton as HTMLButtonElement).disabled).toBe(true);
    expect((organizarButton as HTMLButtonElement).disabled).toBe(true);
  });
});
