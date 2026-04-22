import { render, screen, fireEvent } from "@testing-library/svelte";
import { describe, it, expect } from "vitest";
import SnapshotHistory from "./SnapshotHistory.svelte";
import type { HistoryEntry } from "../../generated-api";

describe("SnapshotHistory.svelte", () => {
  const mockHistory: HistoryEntry[] = [
    {
      id: 1,
      created_at: "2024-01-02T10:30:00Z",
      action_type: "manual_edit",
      changes: {
        added: ["Alice", "Bob"],
        removed: ["Charlie"],
        renamed: [],
        modified: [],
      },
    },
    {
      id: 2,
      created_at: "2024-01-01T09:15:00Z",
      action_type: "notion_sync",
      changes: {
        added: [],
        removed: [],
        renamed: [{ old_name: "Juan", new_name: "Juan Perez" }],
        modified: [
          {
            nombre: "David",
            changes: { is_new: { old: true, new: false } },
          },
        ],
      },
    },
    {
      id: 3,
      created_at: "2024-01-03T15:45:00Z",
      action_type: "creation",
      changes: {
        added: [],
        removed: [],
        renamed: [],
        modified: [],
      },
    },
  ];

  it("renders history summary with correct count", () => {
    render(SnapshotHistory, { props: { history: mockHistory } });

    expect(screen.getByText(/Historial de Cambios \(3\)/)).toBeTruthy();
  });

  it("does not render when history is empty", () => {
    render(SnapshotHistory, { props: { history: [] } });

    expect(screen.queryByText(/Historial de Cambios/)).toBeNull();
  });

  it("renders individual history entries with correct action types", () => {
    render(SnapshotHistory, { props: { history: mockHistory } });

    expect(screen.getByText("Edición Manual")).toBeTruthy();
    expect(screen.getByText("Sincronización Notion")).toBeTruthy();
    expect(screen.getByText("Creación")).toBeTruthy();
  });

  it("displays changes correctly for added players", () => {
    render(SnapshotHistory, { props: { history: mockHistory } });

    expect(screen.getByText("+ Añadidos: Alice, Bob")).toBeTruthy();
  });

  it("displays changes correctly for removed players", () => {
    render(SnapshotHistory, { props: { history: mockHistory } });

    expect(screen.getByText("- Removidos: Charlie")).toBeTruthy();
  });

  it("displays changes correctly for renamed players", () => {
    render(SnapshotHistory, { props: { history: mockHistory } });

    expect(screen.getByText("✏️ Renombrados: Juan ➔ Juan Perez")).toBeTruthy();
  });

  it("displays changes correctly for modified players", () => {
    render(SnapshotHistory, { props: { history: mockHistory } });

    expect(screen.getByText("✏️ Editados:")).toBeTruthy();
    expect(screen.getByText("David:")).toBeTruthy();
    expect(screen.getByText("[is_new: true ➔ false]")).toBeTruthy();
  });

  it("displays 'Sin cambios locales' when no changes exist", () => {
    const noChangesHistory: HistoryEntry[] = [
      {
        id: 1,
        created_at: "2024-01-01T10:00:00Z",
        action_type: "creation",
        changes: {
          added: [],
          removed: [],
          renamed: [],
          modified: [],
        },
      },
    ];

    render(SnapshotHistory, { props: { history: noChangesHistory } });

    expect(screen.getByText("Sin cambios locales")).toBeTruthy();
  });

  it("formats dates correctly", () => {
    render(SnapshotHistory, { props: { history: mockHistory } });

    // Check that formatted dates are displayed
    expect(screen.getByText(/2 ene\./)).toBeTruthy();
    expect(screen.getByText(/1 ene\./)).toBeTruthy();
    expect(screen.getByText(/3 ene\./)).toBeTruthy();
  });

  it("applies correct CSS classes to change types", () => {
    const { container } = render(SnapshotHistory, {
      props: { history: mockHistory },
    });

    // Check that change elements have correct classes
    const addedElement = container.querySelector(".change-added");
    expect(addedElement).toBeTruthy();
    expect(addedElement?.textContent).toContain("Añadidos: Alice, Bob");

    const removedElement = container.querySelector(".change-removed");
    expect(removedElement).toBeTruthy();
    expect(removedElement?.textContent).toContain("Removidos: Charlie");

    const renamedElement = container.querySelector(".change-renamed");
    expect(renamedElement).toBeTruthy();
    expect(renamedElement?.textContent).toContain(
      "Renombrados: Juan ➔ Juan Perez",
    );

    const modifiedElement = container.querySelector(".change-modified");
    expect(modifiedElement).toBeTruthy();
  });

  it("handles multiple modified fields correctly", () => {
    const historyWithMultipleMods: HistoryEntry[] = [
      {
        id: 1,
        created_at: "2024-01-01T10:00:00Z",
        action_type: "manual_edit",
        changes: {
          added: [],
          removed: [],
          renamed: [],
          modified: [
            {
              nombre: "Player1",
              changes: {
                is_new: { old: true, new: false },
                juegos_este_ano: { old: 0, new: 5 },
              },
            },
          ],
        },
      },
    ];

    render(SnapshotHistory, { props: { history: historyWithMultipleMods } });

    expect(screen.getByText("Player1:")).toBeTruthy();
    expect(screen.getByText("[is_new: true ➔ false]")).toBeTruthy();
    expect(screen.getByText("[juegos_este_ano: 0 ➔ 5]")).toBeTruthy();
  });

  it("is collapsed by default", () => {
    const { container } = render(SnapshotHistory, {
      props: { history: mockHistory },
    });

    const details = container.querySelector("details");
    expect(details?.open).toBe(false);
  });

  it("expands when clicked", async () => {
    const { container } = render(SnapshotHistory, {
      props: { history: mockHistory },
    });

    const summary = container.querySelector("summary");
    expect(summary).toBeTruthy();

    // Click to expand
    if (summary) {
      await fireEvent.click(summary);
    }

    const details = container.querySelector("details");
    expect(details?.open).toBe(true);
  });

  it("renders history items in correct order", () => {
    const { container } = render(SnapshotHistory, {
      props: { history: mockHistory },
    });

    const historyItems = container.querySelectorAll(".history-item");
    expect(historyItems).toHaveLength(3);

    // Should be in the order provided in the array
    expect(historyItems[0]?.textContent).toContain("Edición Manual");
    expect(historyItems[1]?.textContent).toContain("Sincronización Notion");
    expect(historyItems[2]?.textContent).toContain("Creación");
  });

  it("handles hover interactions on summary", async () => {
    const { container } = render(SnapshotHistory, {
      props: { history: mockHistory },
    });

    const summary = container.querySelector("summary");
    expect(summary).toBeTruthy();

    // Mouse enter should add hover styles
    if (summary) {
      await fireEvent.mouseEnter(summary);
    }

    // Mouse leave should remove hover styles
    if (summary) {
      await fireEvent.mouseLeave(summary);
    }

    // We can't easily test inline styles in jsdom, but we can verify the events don't crash
    expect(summary).toBeTruthy();
  });

  it("renders with semantic color classes", () => {
    const { container } = render(SnapshotHistory, {
      props: { history: mockHistory },
    });

    // Verify semantic color classes are applied instead of hardcoded colors
    const addedElement = container.querySelector(".change-added");
    expect(addedElement?.classList.contains("change-added")).toBe(true);

    const removedElement = container.querySelector(".change-removed");
    expect(removedElement?.classList.contains("change-removed")).toBe(true);

    const renamedElement = container.querySelector(".change-renamed");
    expect(renamedElement?.classList.contains("change-renamed")).toBe(true);
  });
});
