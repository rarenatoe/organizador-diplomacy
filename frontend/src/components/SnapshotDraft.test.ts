import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";
import SnapshotDraft from "./SnapshotDraft.svelte";

// Mock the API module
vi.mock("../api", () => ({
  createSnapshot: vi.fn().mockResolvedValue({
    snapshot_id: 123,
  }),
  saveSnapshot: vi.fn().mockResolvedValue({
    snapshot_id: 123,
  }),
  fetchNotionPlayers: vi.fn().mockResolvedValue({ players: [] }),
}));

// Mock the utils module
vi.mock("../utils", () => ({
  parsePlayersCsv: vi.fn().mockReturnValue([
    {
      nombre: "Alice",
      experiencia: "Nuevo",
      juegos_este_ano: 0,
      prioridad: 0,
      partidas_deseadas: 1,
      partidas_gm: 0,
    },
    {
      nombre: "Bob",
      experiencia: "Antiguo",
      juegos_este_ano: 3,
      prioridad: 1,
      partidas_deseadas: 2,
      partidas_gm: 1,
    },
  ]),
}));

// Mock the stores
vi.mock("../stores.svelte", () => ({
  setActiveNodeId: vi.fn(),
}));

// Mock window.prompt
const mockPrompt = vi.fn();
vi.stubGlobal("prompt", mockPrompt);

describe("SnapshotDraft", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders with empty state", () => {
    const { container } = render(SnapshotDraft, {
      props: {
        parentId: null,
        initialPlayers: [],
        defaultEventType: "manual",
        onClose: () => {},
        onChainUpdate: () => {},
        onOpenSnapshot: () => {},
        onShowError: () => {},
      },
    });

    expect(container.textContent).toContain("Nueva Versión");
    expect(container.textContent).toContain("No hay jugadores en el borrador");
  });

  it("shows add player and paste CSV buttons", () => {
    render(SnapshotDraft, {
      props: {
        parentId: null,
        initialPlayers: [],
        defaultEventType: "manual",
        onClose: () => {},
        onChainUpdate: () => {},
        onOpenSnapshot: () => {},
        onShowError: () => {},
      },
    });

    expect(screen.getByText("➕ Agregar jugador")).toBeTruthy();
    expect(screen.getByText("📥 Pegar CSV")).toBeTruthy();
  });

  it("adds a player when add button is clicked", async () => {
    mockPrompt.mockReturnValue("Test Player");

    const { container } = render(SnapshotDraft, {
      props: {
        parentId: null,
        initialPlayers: [],
        defaultEventType: "manual",
        onClose: () => {},
        onChainUpdate: () => {},
        onOpenSnapshot: () => {},
        onShowError: () => {},
      },
    });

    const addButton = screen.getByText("➕ Agregar jugador");
    await fireEvent.click(addButton);

    expect(mockPrompt).toHaveBeenCalledWith("Nombre del nuevo jugador:");
    const nameInput = container.querySelector(
      ".player-name-input",
    ) as HTMLInputElement;
    expect(nameInput).toBeTruthy();
    expect(nameInput.value).toBe("Test Player");
  });

  it("opens CSV modal when paste CSV button is clicked", async () => {
    render(SnapshotDraft, {
      props: {
        parentId: null,
        initialPlayers: [],
        defaultEventType: "manual",
        onClose: () => {},
        onChainUpdate: () => {},
        onOpenSnapshot: () => {},
        onShowError: () => {},
      },
    });

    const csvButton = screen.getByText("📥 Pegar CSV");
    await fireEvent.click(csvButton);

    expect(screen.getByText("Pegar CSV")).toBeTruthy();
    expect(screen.getByPlaceholderText(/nombre,experiencia/)).toBeTruthy();
  });

  it("autofocuses textarea when CSV modal opens", async () => {
    render(SnapshotDraft, {
      props: {
        parentId: null,
        initialPlayers: [],
        defaultEventType: "manual",
        onClose: () => {},
        onChainUpdate: () => {},
        onOpenSnapshot: () => {},
        onShowError: () => {},
      },
    });

    const csvButton = screen.getByText("📥 Pegar CSV");
    await fireEvent.click(csvButton);

    const textarea = screen.getByPlaceholderText(/nombre,experiencia/);
    expect(document.activeElement).toBe(textarea);
  });

  it("imports CSV when import button is clicked", async () => {
    const { container } = render(SnapshotDraft, {
      props: {
        parentId: null,
        initialPlayers: [],
        defaultEventType: "manual",
        onClose: () => {},
        onChainUpdate: () => {},
        onOpenSnapshot: () => {},
        onShowError: () => {},
      },
    });

    // Open CSV modal
    const csvButton = screen.getByText("📥 Pegar CSV");
    await fireEvent.click(csvButton);

    // Type in textarea
    const textarea = screen.getByPlaceholderText(/nombre,experiencia/);
    await fireEvent.input(textarea, {
      target: { value: "nombre,experiencia\nAlice,Nuevo\nBob,Antiguo" },
    });

    // Click import
    const importButton = screen.getByText("Importar");
    await fireEvent.click(importButton);

    // Verify players were added by checking input values
    const nameInputs = container.querySelectorAll(".player-name-input");
    expect(nameInputs.length).toBe(2);
    expect((nameInputs[0] as HTMLInputElement).value).toBe("Alice");
    expect((nameInputs[1] as HTMLInputElement).value).toBe("Bob");
  });

  it("closes CSV modal when cancel button is clicked", async () => {
    render(SnapshotDraft, {
      props: {
        parentId: null,
        initialPlayers: [],
        defaultEventType: "manual",
        onClose: () => {},
        onChainUpdate: () => {},
        onOpenSnapshot: () => {},
        onShowError: () => {},
      },
    });

    // Open CSV modal
    const csvButton = screen.getByText("📥 Pegar CSV");
    await fireEvent.click(csvButton);

    expect(screen.getByText("Pegar CSV")).toBeTruthy();

    // Click cancel
    const cancelButton = screen.getByText("Cancelar");
    await fireEvent.click(cancelButton);

    // Modal should be closed
    expect(screen.queryByText("Pegar CSV")).toBeNull();
  });

  it("deletes a player when delete button is clicked", async () => {
    mockPrompt.mockReturnValue("Test Player");

    const { container } = render(SnapshotDraft, {
      props: {
        parentId: null,
        initialPlayers: [],
        defaultEventType: "manual",
        onClose: () => {},
        onChainUpdate: () => {},
        onOpenSnapshot: () => {},
        onShowError: () => {},
      },
    });

    // Add a player
    const addButton = screen.getByText("➕ Agregar jugador");
    await fireEvent.click(addButton);

    const nameInput = container.querySelector(
      ".player-name-input",
    ) as HTMLInputElement;
    expect(nameInput).toBeTruthy();
    expect(nameInput.value).toBe("Test Player");

    // Delete the player
    const deleteButton = container.querySelector(".btn-delete");
    expect(deleteButton).toBeTruthy();
    await fireEvent.click(deleteButton!);

    // Player should be removed - no name input should exist
    const nameInputs = container.querySelectorAll(".player-name-input");
    expect(nameInputs.length).toBe(0);
  });

  it("disables save button when no players", () => {
    render(SnapshotDraft, {
      props: {
        parentId: null,
        initialPlayers: [],
        defaultEventType: "manual",
        onClose: () => {},
        onChainUpdate: () => {},
        onOpenSnapshot: () => {},
        onShowError: () => {},
      },
    });

    const saveButton = screen.getByText("✨ Guardar Nueva Lista");
    expect(saveButton.hasAttribute("disabled")).toBe(true);
  });

  it("enables save button when players exist", async () => {
    mockPrompt.mockReturnValue("Test Player");

    render(SnapshotDraft, {
      props: {
        parentId: null,
        initialPlayers: [],
        defaultEventType: "manual",
        onClose: () => {},
        onChainUpdate: () => {},
        onOpenSnapshot: () => {},
        onShowError: () => {},
      },
    });

    // Add a player
    const addButton = screen.getByText("➕ Agregar jugador");
    await fireEvent.click(addButton);

    const saveButton = screen.getByText("✨ Guardar Nueva Lista");
    expect(saveButton.hasAttribute("disabled")).toBe(false);
  });

  it("calls saveSnapshot when save button is clicked", async () => {
    const { saveSnapshot } = await import("../api");
    const onClose = vi.fn();
    const onChainUpdate = vi.fn();
    const onOpenSnapshot = vi.fn();

    mockPrompt.mockReturnValue("Test Player");

    render(SnapshotDraft, {
      props: {
        parentId: null,
        initialPlayers: [],
        defaultEventType: "manual",
        onClose,
        onChainUpdate,
        onOpenSnapshot,
        onShowError: () => {},
      },
    });

    // Add a player
    const addButton = screen.getByText("➕ Agregar jugador");
    await fireEvent.click(addButton);

    // Save
    const saveButton = screen.getByText("✨ Guardar Nueva Lista");
    await fireEvent.click(saveButton);

    expect(saveSnapshot).toHaveBeenCalledWith({
      parent_id: null,
      event_type: "manual",
      players: [
        {
          nombre: "Test Player",
          experiencia: "Nuevo",
          juegos_este_ano: 0,
          prioridad: 0,
          partidas_deseadas: 1,
          partidas_gm: 0,
        },
      ],
    });
  });

  it("updates player prioridad when checkbox is changed", async () => {
    mockPrompt.mockReturnValue("Test Player");

    const { container } = render(SnapshotDraft, {
      props: {
        parentId: null,
        initialPlayers: [],
        defaultEventType: "manual",
        onClose: () => {},
        onChainUpdate: () => {},
        onOpenSnapshot: () => {},
        onShowError: () => {},
      },
    });

    // Add a player
    const addButton = screen.getByText("➕ Agregar jugador");
    await fireEvent.click(addButton);

    // Find and click the prioridad checkbox
    const prioCheckbox = container.querySelector(
      'input[type="checkbox"]',
    ) as HTMLInputElement;
    expect(prioCheckbox).toBeTruthy();
    await fireEvent.click(prioCheckbox);

    // Checkbox should be checked
    expect(prioCheckbox.checked).toBe(true);
  });

  it("pre-populates players from initialPlayers prop", () => {
    const { container } = render(SnapshotDraft, {
      props: {
        parentId: 1,
        initialPlayers: [
          {
            nombre: "Alice",
            experiencia: "Nuevo",
            juegos_este_ano: 0,
            prioridad: 0,
            partidas_deseadas: 1,
            partidas_gm: 0,
          },
          {
            nombre: "Bob",
            experiencia: "Antiguo",
            juegos_este_ano: 3,
            prioridad: 1,
            partidas_deseadas: 2,
            partidas_gm: 1,
          },
        ],
        defaultEventType: "manual",
        onClose: () => {},
        onChainUpdate: () => {},
        onOpenSnapshot: () => {},
        onShowError: () => {},
      },
    });

    const nameInputs = container.querySelectorAll(".player-name-input");
    expect(nameInputs.length).toBe(2);
    expect((nameInputs[0] as HTMLInputElement).value).toBe("Alice");
    expect((nameInputs[1] as HTMLInputElement).value).toBe("Bob");
  });

  it("updates player partidas_deseadas when number input is changed", async () => {
    mockPrompt.mockReturnValue("Test Player");

    const { container } = render(SnapshotDraft, {
      props: {
        parentId: null,
        initialPlayers: [],
        defaultEventType: "manual",
        onClose: () => {},
        onChainUpdate: () => {},
        onOpenSnapshot: () => {},
        onShowError: () => {},
      },
    });

    // Add a player
    const addButton = screen.getByText("➕ Agregar jugador");
    await fireEvent.click(addButton);

    // Find and change the deseadas input
    const deseadasInput = container.querySelector(
      'input[type="number"]',
    ) as HTMLInputElement;
    expect(deseadasInput).toBeTruthy();
    await fireEvent.input(deseadasInput, { target: { value: "3" } });

    // Input should have new value
    expect(deseadasInput.value).toBe("3");
  });

  it("calls onShowError when importing CSV yields no valid players", async () => {
    const { parsePlayersCsv } = await import("../utils");
    (parsePlayersCsv as ReturnType<typeof vi.fn>).mockReturnValueOnce([]);

    const onShowError = vi.fn();
    render(SnapshotDraft, {
      props: {
        parentId: null,
        initialPlayers: [],
        defaultEventType: "manual",
        onClose: () => {},
        onChainUpdate: () => {},
        onOpenSnapshot: () => {},
        onShowError,
      },
    });

    await fireEvent.click(screen.getByText("📥 Pegar CSV"));
    const textarea = screen.getByPlaceholderText(/nombre,experiencia/);
    await fireEvent.input(textarea, {
      target: { value: "bad,csv" },
    });
    await fireEvent.click(screen.getByText("Importar"));

    expect(onShowError).toHaveBeenCalledWith(
      "Aviso / Error",
      "No se encontraron jugadores válidos en el CSV",
    );
  });

  it("calls onShowError when saving with no players", async () => {
    const onShowError = vi.fn();
    render(SnapshotDraft, {
      props: {
        parentId: null,
        initialPlayers: [],
        defaultEventType: "manual",
        onClose: () => {},
        onChainUpdate: () => {},
        onOpenSnapshot: () => {},
        onShowError,
      },
    });

    await fireEvent.click(screen.getByText("✨ Guardar Nueva Lista"));
    expect(onShowError).toHaveBeenCalledWith(
      "Aviso / Error",
      "Agrega al menos un jugador antes de guardar",
    );
  });
});
