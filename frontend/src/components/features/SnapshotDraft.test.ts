import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";
import SnapshotDraft from "./SnapshotDraft.svelte";

// Mock the API module
vi.mock("../../api", () => ({
  createSnapshot: vi.fn().mockResolvedValue({
    snapshot_id: 123,
  }),
  saveSnapshot: vi.fn().mockResolvedValue({
    snapshot_id: 123,
  }),
  fetchNotionPlayers: vi
    .fn()
    .mockResolvedValue({ players: [], similar_names: [] }),
  getAllPlayers: vi
    .fn()
    .mockResolvedValue({ names: ["Daniel Eiler", "Daniel Escobar"] }),
  checkPlayerSimilarity: vi.fn().mockResolvedValue({ similarities: [] }),
  lookupPlayerHistory: vi.fn().mockResolvedValue({ players: {} }),
}));

// Mock the utils module
vi.mock("../../utils", () => ({
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
vi.mock("../../stores.svelte", () => ({
  setActiveNodeId: vi.fn(),
}));

describe("SnapshotDraft", () => {
  const mockInitialPlayers = [
    {
      nombre: "Test Player",
      experiencia: "Nuevo",
      juegos_este_ano: 0,
      prioridad: 0,
      partidas_deseadas: 1,
      partidas_gm: 0,
      original_nombre: "Test Player",
      historyRestored: false,
    },
  ];
  const defaultProps = {
    parentId: null,
    initialPlayers: [],
    defaultEventType: "manual" as const,
    onClose: vi.fn(),
    onCancel: vi.fn(),
    onChainUpdate: vi.fn(),
    onOpenSnapshot: vi.fn(),
    onShowError: vi.fn(),
  };

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
        onCancel: () => {},
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
        onCancel: () => {},
        onChainUpdate: () => {},
        onOpenSnapshot: () => {},
        onShowError: () => {},
      },
    });

    expect(screen.getByText("➕ Agregar jugador")).toBeTruthy();
    expect(screen.getByText("📥 Pegar CSV")).toBeTruthy();
  });

  it("renders autocomplete input inside table footer when add button is clicked", async () => {
    const { tick } = await import("svelte");
    render(SnapshotDraft, {
      props: { ...defaultProps, initialPlayers: mockInitialPlayers },
    });
    await fireEvent.click(screen.getByText("➕ Agregar jugador"));
    await tick();
    expect(
      screen.getByPlaceholderText("Escribe para buscar o agregar..."),
    ).toBeTruthy();
  });

  it("filters known players in dropdown", async () => {
    const { tick } = await import("svelte");
    render(SnapshotDraft, {
      props: { ...defaultProps, initialPlayers: mockInitialPlayers },
    });
    await fireEvent.click(screen.getByText("➕ Agregar jugador"));
    await tick();
    const input = screen.getByPlaceholderText(
      "Escribe para buscar o agregar...",
    );
    await fireEvent.input(input, { target: { value: "Dan" } });
    expect(screen.getByText("Daniel Eiler")).toBeInTheDocument();
    expect(screen.getByText("Daniel Escobar")).toBeInTheDocument();
  });

  it("rehydrates player history when suggested name is clicked", async () => {
    const { tick } = await import("svelte");
    const { lookupPlayerHistory } = await import("../../api");
    (lookupPlayerHistory as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      players: {
        // eslint-disable-next-line @typescript-eslint/naming-convention
        "Daniel Eiler": {
          experiencia: "Veterano",
          juegos_este_ano: 5,
          prioridad: 1,
          partidas_deseadas: 2,
          partidas_gm: 0,
          source: "history",
        },
      },
    });
    render(SnapshotDraft, {
      props: { ...defaultProps, initialPlayers: mockInitialPlayers },
    });
    await fireEvent.click(screen.getByText("➕ Agregar jugador"));
    await tick();
    const input = screen.getByPlaceholderText(
      "Escribe para buscar o agregar...",
    );
    await fireEvent.input(input, { target: { value: "Dan" } });
    await fireEvent.click(screen.getByText("Daniel Eiler"));
    expect(
      screen.queryByPlaceholderText("Escribe para buscar o agregar..."),
    ).toBeNull();
    const nameInputs = screen.getAllByPlaceholderText("Nombre del jugador");
    expect(nameInputs.length).toBe(2); // Original player + new player
    expect((nameInputs[1] as HTMLInputElement).value).toBe("Daniel Eiler");
  });

  it("opens CSV modal when paste CSV button is clicked", async () => {
    render(SnapshotDraft, {
      props: {
        parentId: null,
        initialPlayers: [],
        defaultEventType: "manual",
        onClose: () => {},
        onCancel: () => {},
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

  it("pauses CSV import and shows sync modal when similarities are found", async () => {
    const { checkPlayerSimilarity } = await import("../../api");
    (checkPlayerSimilarity as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      similarities: [
        { notion: "Daniel Eiler", snapshot: "Daniel Ei", similarity: 0.95 },
      ],
    });

    const { container } = render(SnapshotDraft, { props: defaultProps });

    await fireEvent.click(screen.getByText("📥 Pegar CSV"));
    const textarea = screen.getByPlaceholderText(/nombre,experiencia/);
    await fireEvent.input(textarea, {
      target: { value: "nombre,experiencia\nDaniel Ei,Nuevo" },
    });
    await fireEvent.click(screen.getByText("Importar"));

    // Verify it paused: The table should NOT have the player yet
    const nameInputs = container.querySelectorAll(".table-input-ghost");
    expect(nameInputs.length).toBe(0);

    // Verify interruption: Sync modal should be visible
    expect(screen.getByText(/Nombres similares/i)).toBeInTheDocument();
  });

  it("autofocuses textarea when CSV modal opens", async () => {
    render(SnapshotDraft, {
      props: {
        parentId: null,
        initialPlayers: [],
        defaultEventType: "manual",
        onClose: () => {},
        onCancel: () => {},
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
        onCancel: () => {},
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
    const nameInputs = container.querySelectorAll(".table-input-ghost");
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
        onCancel: () => {},
        onChainUpdate: () => {},
        onOpenSnapshot: () => {},
        onShowError: () => {},
      },
    });

    // Open CSV modal
    const csvButton = screen.getByText("📥 Pegar CSV");
    await fireEvent.click(csvButton);

    expect(screen.getByText("Pegar CSV")).toBeTruthy();

    // Click cancel button in the modal (not the footer button)
    const allCancelButtons = screen.getAllByText("Cancelar");
    // The modal cancel button should be the last one (inside the modal)
    const modalCancelButton = allCancelButtons[allCancelButtons.length - 1];
    await fireEvent.click(modalCancelButton!);

    // Modal should be closed
    expect(screen.queryByText("Pegar CSV")).toBeNull();
  });

  it("deletes a player when delete button is clicked", async () => {
    const { container } = render(SnapshotDraft, {
      props: { ...defaultProps, initialPlayers: mockInitialPlayers },
    });
    const deleteButton = screen.getByTitle("Eliminar");
    await fireEvent.click(deleteButton);
    expect(container.querySelectorAll(".table-input-ghost").length).toBe(0);
  });

  it("disables save button when no players", () => {
    render(SnapshotDraft, {
      props: {
        parentId: null,
        initialPlayers: [],
        defaultEventType: "manual",
        onClose: () => {},
        onCancel: () => {},
        onChainUpdate: () => {},
        onOpenSnapshot: () => {},
        onShowError: () => {},
      },
    });

    const saveButton = screen.getByRole("button", {
      name: /Guardar Nueva Lista/i,
    });
    expect(saveButton).toBeDisabled();
  });

  it("enables save button when players exist", () => {
    render(SnapshotDraft, {
      props: { ...defaultProps, initialPlayers: mockInitialPlayers },
    });
    const saveButton = screen.getByRole("button", {
      name: /Guardar Nueva Lista/i,
    });
    expect(saveButton).not.toBeDisabled();
  });

  it("calls saveSnapshot when save button is clicked", async () => {
    const { saveSnapshot } = await import("../../api");
    render(SnapshotDraft, {
      props: { ...defaultProps, initialPlayers: mockInitialPlayers },
    });
    await fireEvent.click(
      screen.getByRole("button", { name: /Guardar Nueva Lista/i }),
    );
    expect(saveSnapshot).toHaveBeenCalled();
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
        onCancel: () => {},
        onChainUpdate: () => {},
        onOpenSnapshot: () => {},
        onShowError: () => {},
      },
    });

    const nameInputs = container.querySelectorAll(".table-input-ghost");
    expect(nameInputs.length).toBe(2);
    expect((nameInputs[0] as HTMLInputElement).value).toBe("Alice");
    expect((nameInputs[1] as HTMLInputElement).value).toBe("Bob");
  });

  it("calls onShowError when importing CSV yields no valid players", async () => {
    const { parsePlayersCsv } = await import("../../utils");
    (parsePlayersCsv as ReturnType<typeof vi.fn>).mockReturnValueOnce([]);

    const onShowError = vi.fn();
    render(SnapshotDraft, {
      props: {
        parentId: null,
        initialPlayers: [],
        defaultEventType: "manual",
        onClose: () => {},
        onCancel: () => {},
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
      "CSV Inválido",
      "No se encontraron jugadores válidos en el archivo.",
    );
  });

  it("shows disabled save button with title when no players", () => {
    const onShowError = vi.fn();
    render(SnapshotDraft, {
      props: {
        parentId: null,
        initialPlayers: [],
        defaultEventType: "manual",
        onClose: () => {},
        onCancel: () => {},
        onChainUpdate: () => {},
        onOpenSnapshot: () => {},
        onShowError,
      },
    });

    const saveButton = screen.getByRole("button", {
      name: /Guardar Nueva Lista/i,
    });
    // Verify button is disabled and has helpful title
    expect(saveButton).toBeDisabled();
    expect(saveButton).toHaveAttribute(
      "title",
      "Agrega al menos un jugador para guardar",
    );
  });

  it("sends renames payload when player name is edited", async () => {
    const { saveSnapshot } = await import("../../api");
    const onClose = vi.fn();
    const onChainUpdate = vi.fn();

    const { container } = render(SnapshotDraft, {
      props: {
        parentId: 1,
        initialPlayers: [
          {
            nombre: "Daniel V.",
            experiencia: "Antiguo",
            juegos_este_ano: 5,
            prioridad: 1,
            partidas_deseadas: 2,
            partidas_gm: 1,
          },
        ],
        defaultEventType: "manual",
        onClose,
        onCancel: () => {},
        onChainUpdate,
        onOpenSnapshot: () => {},
        onShowError: () => {},
      },
    });

    // Find and edit the player name input
    const nameInput = container.querySelector(
      ".table-input-ghost",
    ) as HTMLInputElement;
    expect(nameInput).toBeTruthy();
    expect(nameInput.value).toBe("Daniel V.");

    // Change the name
    await fireEvent.input(nameInput, {
      target: { value: "Daniel Villafranca" },
    });
    expect(nameInput.value).toBe("Daniel Villafranca");

    // Save
    const saveButton = screen.getByRole("button", {
      name: /Guardar Edición/i,
    });
    await fireEvent.click(saveButton);

    // Verify saveSnapshot was called with renames payload
    expect(saveSnapshot).toHaveBeenCalledWith({
      parent_id: 1,
      event_type: "manual",
      players: [
        {
          nombre: "Daniel Villafranca",
          experiencia: "Antiguo",
          juegos_este_ano: 5,
          prioridad: 1,
          partidas_deseadas: 2,
          partidas_gm: 1,
        },
      ],
      renames: [{ from: "Daniel V.", to: "Daniel Villafranca" }],
    });
  });

  it("oculta los botones de CSV y Notion al editar (parentId no es nulo)", () => {
    render(SnapshotDraft, {
      props: {
        parentId: 123, // Editando una lista existente
        initialPlayers: [
          {
            nombre: "Jugador Existente",
            experiencia: "Antiguo",
            juegos_este_ano: 5,
            prioridad: 1,
            partidas_deseadas: 2,
            partidas_gm: 1,
            original_nombre: "Jugador Existente",
          },
        ],
        defaultEventType: "edit",
        onClose: vi.fn(),
        onCancel: vi.fn(),
        onChainUpdate: vi.fn(),
        onOpenSnapshot: vi.fn(),
        onShowError: vi.fn(),
      },
    });

    // Los botones de CSV y Notion NO deben estar presentes
    expect(screen.queryByText("📥 Pegar CSV")).toBeNull();
    expect(screen.queryByText(/Importar Notion/)).toBeNull();

    // El botón de agregar jugador SÍ debe estar presente
    expect(screen.getByText("➕ Agregar jugador")).toBeTruthy();
  });
});
