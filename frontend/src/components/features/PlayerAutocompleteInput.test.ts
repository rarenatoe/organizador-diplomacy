import { beforeEach, describe, expect, it, vi } from "vitest";

import { fireEvent, render, screen, waitFor } from "@testing-library/svelte";

import * as api from "../../generated-api";
import { mockApiSuccess } from "../../tests/mockHelpers";
import PlayerAutocompleteInput from "./PlayerAutocompleteInput.svelte";

describe("PlayerAutocompleteInput", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("should auto-select known player on exact match when Enter is pressed", async () => {
    const mockConfirm = vi.fn();
    // Simulate your AutocompletePlayer[] type
    const mockKnownPlayers = [
      {
        notion_id: "1",
        nombre: "Alice",
        display: "Alice",
        is_local: true,
        is_alias: false,
      },
      {
        notion_id: "2",
        nombre: "Bob",
        display: "Bob",
        is_local: false,
        is_alias: true,
      },
    ];

    render(PlayerAutocompleteInput, {
      props: {
        value: "Al",
        knownPlayers: mockKnownPlayers, // Use the correct prop name here!
        onConfirm: mockConfirm,
      },
    });

    const input = screen.getByRole("textbox");

    await fireEvent.input(input, { target: { value: "Alice" } });
    await fireEvent.keyDown(input, { key: "Enter" });

    expect(mockConfirm).toHaveBeenCalledOnce();
    expect(mockConfirm).toHaveBeenCalledWith(
      expect.objectContaining({ notion_id: "1", nombre: "Alice" }),
      false,
    );
  });

  it("should blur the input after pressing Enter", async () => {
    const mockConfirm = vi.fn();
    render(PlayerAutocompleteInput, {
      props: {
        value: "Al",
        knownPlayers: [],
        onConfirm: mockConfirm,
      },
    });

    const input = screen.getByRole("textbox");
    input.focus();
    expect(document.activeElement).toBe(input);

    await fireEvent.keyDown(input, { key: "Enter" });

    expect(document.activeElement).not.toBe(input);
  });

  it("should securely unfocus the input only when a player is confirmed", async () => {
    const mockConfirm = vi.fn();
    render(PlayerAutocompleteInput, {
      props: {
        value: "Al",
        knownPlayers: [],
        onConfirm: mockConfirm,
      },
    });

    const input = screen.getByRole("textbox");
    input.focus();
    expect(document.activeElement).toBe(input);

    // Mock empty similarities to force an immediate confirmation rather than opening the modal
    vi.spyOn(api, "apiPlayerCheckSimilarity").mockResolvedValueOnce(
      mockApiSuccess<api.ApiPlayerCheckSimilarityResponse>({
        similarities: [],
      }),
    );

    await fireEvent.keyDown(input, { key: "Enter" });

    // Wait for the async API check to complete and executeConfirm to run
    await waitFor(() => {
      expect(mockConfirm).toHaveBeenCalled();
      expect(document.activeElement).not.toBe(input);
    });
  });

  it("should remove active-dropdown class immediately when resolution modal pops up", async () => {
    const { tick } = await import("svelte");
    const mockConfirm = vi.fn();

    vi.spyOn(api, "apiPlayerCheckSimilarity").mockResolvedValueOnce(
      mockApiSuccess<api.ApiPlayerCheckSimilarityResponse>({
        similarities: [
          {
            notion_id: "1",
            notion_name: "Alice Real",
            snapshot: "Alic",
            similarity: 0.9,
            match_method: "fuzzy",
          },
        ],
      }),
    );

    const { container } = render(PlayerAutocompleteInput, {
      props: {
        value: "",
        knownPlayers: [
          {
            display: "Alice Typo",
            nombre: "Alice Typo",
            is_local: false,
            is_alias: false,
          },
        ],
        onConfirm: mockConfirm,
      },
    });

    const input = screen.getByRole("textbox");

    // Type a substring of the known player so the suggestions array > 0
    await fireEvent.input(input, { target: { value: "Alic" } });
    await tick();

    const wrapper = container.querySelector("div");
    expect(wrapper).not.toBeNull();

    // Now it will successfully have the class!
    expect(wrapper?.className).toContain("active-dropdown");

    // Press Enter to trigger the similarity modal
    await fireEvent.keyDown(input, { key: "Enter" });

    // Flush promises
    await tick();
    await new Promise((r) => setTimeout(r, 0));
    await tick();

    // Verify the dropdown closes immediately when the modal opens
    expect(wrapper?.className).not.toContain("active-dropdown");
  });
});
