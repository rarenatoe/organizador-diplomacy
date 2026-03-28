import { describe, it, expect, vi } from "vitest";
import { render, fireEvent, screen } from "@testing-library/svelte";
import Header from "./Header.svelte";

describe("Header", () => {
  it("renders header correctly", () => {
    const onNewDraft = vi.fn();

    render(Header, {
      props: {
        onNewDraft,
      },
    });

    expect(screen.getByRole("heading", { level: 1 })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1 }).textContent).toContain(
      "Organizador Diplomacy",
    );
  });

  it("shows Nueva Lista button", () => {
    const onNewDraft = vi.fn();

    render(Header, {
      props: {
        onNewDraft,
      },
    });

    const newListaButton = screen.getByRole("button", { name: /Nueva Lista/i });
    expect(newListaButton).toBeInTheDocument();
    expect(newListaButton.textContent).toContain("Nueva Lista");
  });

  it("clicking Nueva Lista button calls onNewDraft", async () => {
    const onNewDraft = vi.fn();

    render(Header, {
      props: {
        onNewDraft,
      },
    });

    const newListaButton = screen.getByRole("button", { name: /Nueva Lista/i });
    await fireEvent.click(newListaButton);

    expect(onNewDraft).toHaveBeenCalledTimes(1);
  });

  it("Nueva Lista button uses btn-primary class", () => {
    const onNewDraft = vi.fn();

    render(Header, {
      props: {
        onNewDraft,
      },
    });

    const newListaButton = screen.getByRole("button", { name: /Nueva Lista/i });
    expect(newListaButton).toBeInTheDocument();
    expect(newListaButton.classList.contains("btn-primary")).toBe(true);
  });
});
