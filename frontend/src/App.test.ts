import { describe, it, expect, beforeEach } from "vitest";
import { nav } from "./navigation.svelte";
import type { EditPlayerRow } from "./types";

describe("App Integration - Draft State Reset", () => {
  const mockExistingPlayers: EditPlayerRow[] = [
    {
      nombre: "Alice",
      is_new: true,
      juegos_este_ano: 0,
      has_priority: false,
      partidas_deseadas: 1,
      partidas_gm: 0,
      oldName: "Alice",
      historyRestored: false,
    },
    {
      nombre: "Bob",
      is_new: false,
      juegos_este_ano: 3,
      has_priority: true,
      partidas_deseadas: 2,
      partidas_gm: 1,
      oldName: "Bob",
      historyRestored: false,
    },
  ];

  beforeEach(() => {
    nav.close(); // Ensure clean slate before each test
  });

  it("verifies state isolation and unique draft keys when opening different drafts", () => {
    // 1. Simulate opening an existing draft (Editar)
    const existingDraftKey = Date.now();
    nav.push({
      title: "Editando #123",
      type: "draft",
      id: 123,
      draftProps: {
        parentId: 123,
        saveEventType: "manual",
        autoAction: null,
        initialPlayers: mockExistingPlayers,
        initialData: null,
        editingGameId: null,
        draftKey: existingDraftKey,
      },
    });

    expect(nav.current?.type).toBe("draft");
    expect(nav.current?.draftProps?.initialPlayers).toHaveLength(2);
    expect(nav.current?.draftProps?.parentId).toBe(123);

    // 2. Simulate clicking "Nueva Lista" (which clears the stack and pushes a new draft)
    const newDraftKey = Date.now() + 1000; // Simulate time passing
    nav.clearAndPush({
      title: "Nueva Lista",
      type: "draft",
      id: null,
      draftProps: {
        parentId: null,
        saveEventType: "manual",
        autoAction: null,
        initialPlayers: [],
        initialData: null,
        editingGameId: null,
        draftKey: newDraftKey,
      },
    });

    // 3. Verify the new state is completely isolated from the previous state
    expect(nav.current?.type).toBe("draft");
    expect(nav.current?.draftProps?.initialPlayers).toHaveLength(0);
    expect(nav.current?.draftProps?.parentId).toBeNull();
    expect(nav.current?.draftProps?.draftKey).not.toBe(existingDraftKey);

    // Because draftKey is different, Svelte's {#key} block will guarantee component destruction
  });

  it("verifies the stack is correctly managed when popping out of a draft", () => {
    // Setup a snapshot view
    nav.clearAndPush({ title: "Snapshot #1", type: "snapshot", id: 1 });

    // Drill down into a draft
    nav.push({
      title: "Editando #1",
      type: "draft",
      id: 1,
      draftProps: {
        parentId: 1,
        saveEventType: "manual",
        autoAction: null,
        initialPlayers: [],
        initialData: null,
        editingGameId: null,
        draftKey: Date.now(),
      },
    });

    expect(nav.stack).toHaveLength(2);
    expect(nav.current?.type).toBe("draft");

    // Simulate clicking "Cancelar"
    nav.pop();

    expect(nav.stack).toHaveLength(1);
    expect(nav.current?.type).toBe("snapshot");
    expect(nav.current?.title).toBe("Snapshot #1");
  });
});
