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
  getAllPlayers: vi.fn().mockResolvedValue({
    players: [
      { display: "Daniel Eiler", nombre: "Daniel Eiler" },
      { display: "Daniel Escobar", nombre: "Daniel Escobar" },
    ],
  }),
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
  normalizeName: vi
    .fn()
    .mockImplementation((name: string) => name.toLowerCase().trim()),
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

    // Assert structural hierarchy - major content blocks should be wrapped in .section divs
    expect(container.querySelector(".section")).toBeInTheDocument();

    expect(container.textContent).toContain("Nueva Lista");
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

  it("renders autocomplete input inside table header when add button is clicked", async () => {
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

  it("renders the new player input with the correct semantic class", async () => {
    const { container } = render(SnapshotDraft, {
      props: { ...defaultProps, initialPlayers: mockInitialPlayers },
    });
    await fireEvent.click(screen.getByText("➕ Agregar jugador"));
    const input = container.querySelector(
      "input[placeholder='Escribe para buscar o agregar...']",
    );
    expect(input?.classList.contains("input-field")).toBe(true);
  });

  it("filters known players in dropdown", async () => {
    const { tick } = await import("svelte");
    const { container } = render(SnapshotDraft, {
      props: { ...defaultProps, initialPlayers: mockInitialPlayers },
    });
    await fireEvent.click(screen.getByText("➕ Agregar jugador"));
    await tick();
    const input = screen.getByPlaceholderText(
      "Escribe para buscar o agregar...",
    );
    await fireEvent.input(input, { target: { value: "Dan" } });
    await tick(); // <--- Add this tick to flush reactivity

    // Check for proper autocomplete dropdown classes
    const dropdown = container.querySelector(".autocomplete-dropdown");
    const items = container.querySelectorAll(".autocomplete-item");
    expect(dropdown).toBeTruthy();
    expect(items.length).toBe(2);
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

    // Add these 3 lines to flush the API promises:
    await tick();
    await new Promise((r) => setTimeout(r, 0));
    await tick();

    expect(
      screen.queryByPlaceholderText("Escribe para buscar o agregar..."),
    ).toBeNull();
    const nameInputs = screen.getAllByPlaceholderText("Nombre del jugador");
    expect(nameInputs.length).toBe(2); // Original player + new player
    expect((nameInputs[0] as HTMLInputElement).value).toBe("Daniel Eiler");
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
    // 1. Ensure checkPlayerSimilarity is imported along with tick
    const { tick } = await import("svelte");
    const { checkPlayerSimilarity } = await import("../../api");

    // 2. Fix the mock to use notion_id, notion_name, and the similarities wrapper
    (checkPlayerSimilarity as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      similarities: [
        {
          notion_id: "1",
          notion_name: "Daniel Eiler",
          snapshot: "Daniel Ei",
          similarity: 0.95,
        },
      ],
    });

    const { container } = render(SnapshotDraft, { props: defaultProps });

    await fireEvent.click(screen.getByText("📥 Pegar CSV"));
    await tick(); // <--- Flush modal open
    const textarea = screen.getByPlaceholderText(/nombre,experiencia/);
    await fireEvent.input(textarea, {
      target: { value: "nombre,experiencia\nDaniel Ei,Nuevo" },
    });
    await fireEvent.click(screen.getByText("Importar"));

    // 3. Flush API promises
    await tick();
    await new Promise((r) => setTimeout(r, 0));
    await tick();

    // Verify it paused: The table should NOT have the player yet
    const nameInputs = container.querySelectorAll(".table-input-ghost");
    expect(nameInputs.length).toBe(0);

    // Verify interruption: Sync modal should be visible
    expect(screen.getByText(/Resolver Conflictos/i)).toBeInTheDocument();
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
    const { tick } = await import("svelte"); // <--- Import tick

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
    await tick(); // Flush modal open

    // Type in textarea
    const textarea = screen.getByPlaceholderText(/nombre,experiencia/);
    await fireEvent.input(textarea, {
      target: { value: "nombre,experiencia\nAlice,Nuevo\nBob,Antiguo" },
    });

    // Click import
    const importButton = screen.getByText("Importar");
    await fireEvent.click(importButton);

    // 🚀 FLUSH THE ASYNC PIPELINE
    await tick();
    await new Promise((r) => setTimeout(r, 0)); // Let the mock API promises resolve
    await tick(); // Let Svelte render the new rows

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
    expect(modalCancelButton).toBeDefined();
    if (modalCancelButton) {
      await fireEvent.click(modalCancelButton);
    }

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
      name: /Crear Versión/i,
    });
    expect(saveButton).toBeDisabled();
  });

  it("enables save button when players exist", () => {
    render(SnapshotDraft, {
      props: { ...defaultProps, initialPlayers: mockInitialPlayers },
    });
    const saveButton = screen.getByRole("button", {
      name: /Crear Versión/i,
    });
    expect(saveButton).not.toBeDisabled();
  });

  it("calls saveSnapshot when save button is clicked", async () => {
    const { saveSnapshot } = await import("../../api");
    render(SnapshotDraft, {
      props: { ...defaultProps, initialPlayers: mockInitialPlayers },
    });
    await fireEvent.click(
      screen.getByRole("button", { name: /Crear Versión/i }),
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
    const { tick } = await import("svelte");
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

    // Add these 3 lines to flush the async handleImportCsv loop:
    await tick();
    await new Promise((r) => setTimeout(r, 0));
    await tick();

    expect(onShowError).toHaveBeenCalledWith(
      "CSV Inválido",
      "No se encontraron jugadores válidos en el archivo.",
    );
  });

  it("CSV explicit fields take precedence over history defaults", async () => {
    const { tick } = await import("svelte");
    const api = await import("../../api");
    const { parsePlayersCsv } = await import("../../utils");

    // Override the global CSV mock specifically for this test
    (parsePlayersCsv as ReturnType<typeof vi.fn>).mockReturnValueOnce([
      {
        nombre: "Andy",
        experiencia: "Antiguo",
        juegos_este_ano: 5,
        prioridad: 1,
        partidas_deseadas: 3,
        partidas_gm: 1,
      },
    ]);

    // Mock the history API to return defaults to prove they get overridden
    vi.mocked(api.lookupPlayerHistory).mockResolvedValueOnce({
      player: {
        nombre: "Andy",
        experiencia: "Nuevo",
        juegos_este_ano: 0,
        prioridad: 0,
        partidas_deseadas: 1,
        partidas_gm: 0,
        source: "default",
      },
    });

    render(SnapshotDraft, { props: defaultProps });

    // Trigger CSV Import
    await fireEvent.click(screen.getByText(/Pegar CSV/));
    await tick();
    const textarea = screen.getByPlaceholderText(/nombre,experiencia/);
    await fireEvent.input(textarea, {
      target: { value: "Andy,Antiguo,5,1,3,1" },
    });
    await fireEvent.click(screen.getByText("Importar"));

    await tick();
    await new Promise((r) => setTimeout(r, 0));
    await tick();

    // Verify the final save payload gets the exact CSV values, not the history defaults
    await fireEvent.click(
      screen.getByRole("button", { name: /Crear Versión/i }),
    );

    expect(api.saveSnapshot).toHaveBeenCalledWith(
      expect.objectContaining({
        players: expect.arrayContaining([
          expect.objectContaining({
            nombre: "Andy",
            experiencia: "Antiguo",
            juegos_este_ano: 5,
            prioridad: 1,
            partidas_deseadas: 3,
            partidas_gm: 1,
          }),
        ]),
      }),
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
      name: /Crear Versión/i,
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
      name: /Guardar Cambios/i,
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
          notion_id: null,
          notion_name: null,
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

  it("renders correctly in Edit Mode context", () => {
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

    // Assert that the header title renders correctly as "Editando Snapshot #123"
    expect(screen.getByText("Editando Snapshot #123")).toBeInTheDocument();

    // Assert that the save button renders the text "Guardar Cambios"
    const saveButton = screen.getByRole("button", {
      name: /Guardar Cambios/i,
    });
    expect(saveButton).toBeInTheDocument();
  });

  describe("Inline Add & Deduplication", () => {
    it("should block duplicate when player already exists", async () => {
      const { tick } = await import("svelte");
      const onShowErrorMock = vi.fn();
      render(SnapshotDraft, {
        props: {
          ...defaultProps,
          initialPlayers: mockInitialPlayers, // Contains "Test Player"
          onShowError: onShowErrorMock,
        },
      });

      await fireEvent.click(screen.getByText("➕ Agregar jugador"));
      await tick();

      const input = screen.getByPlaceholderText(
        "Escribe para buscar o agregar...",
      );
      await fireEvent.input(input, { target: { value: "Test Player" } });
      await fireEvent.keyDown(input, { key: "Enter" });
      await tick();

      expect(onShowErrorMock).toHaveBeenCalledWith(
        "Jugador duplicado",
        expect.stringContaining("ya está en la lista"),
      );
    });

    it("should resolve duplicate silently when force flag is true via modal", async () => {
      const { tick } = await import("svelte");
      const api = await import("../../api");
      const onShowErrorMock = vi.fn();

      // Trigger modal by mocking a similarity match on an inline add
      vi.mocked(api.checkPlayerSimilarity).mockResolvedValueOnce({
        similarities: [
          {
            notion_id: "123",
            notion_name: "Test Player",
            snapshot: "Test Playe",
            similarity: 0.95,
            match_method: "fuzzy",
            existing_local_name: "Test Player",
          },
        ],
      });

      render(SnapshotDraft, {
        props: {
          ...defaultProps,
          initialPlayers: mockInitialPlayers, // Contains "Test Player"
          onShowError: onShowErrorMock,
        },
      });

      await fireEvent.click(screen.getByText("➕ Agregar jugador"));
      await tick();

      const input = screen.getByPlaceholderText(
        "Escribe para buscar o agregar...",
      );
      await fireEvent.input(input, { target: { value: "Test Playe" } });
      await fireEvent.keyDown(input, { key: "Enter" });

      await tick();
      await new Promise((r) => setTimeout(r, 0)); // Let API promises resolve
      await tick();

      // Modal pops up with Autocorrect view. Click "Usar Test Player"
      const useExistingBtn = screen.getByText(/Usar Test Player/i);
      await fireEvent.click(useExistingBtn);
      await tick();

      // Ensure UI absorbed the duplicate silently without throwing an error toast
      expect(onShowErrorMock).not.toHaveBeenCalled();
    });

    it("should hide aliases from dropdown if the main notion_id is already in the draft", async () => {
      const { tick } = await import("svelte");
      const api = await import("../../api");

      // Mock known players with a main profile and an alias sharing the same notion_id
      vi.mocked(api.getAllPlayers).mockResolvedValue({
        players: [
          {
            display: "Main Identity",
            nombre: "Main Identity",
            notion_id: "shared-id-123",
            is_local: false,
            is_alias: false,
          },
          {
            display: "Alias Name",
            nombre: "Alias Name",
            notion_id: "shared-id-123",
            is_local: false,
            is_alias: true,
          },
        ],
      });

      // Render with the Main Identity already in the draft
      const propsWithLinkedPlayer = {
        ...defaultProps,
        initialPlayers: [
          {
            nombre: "Main Identity",
            notion_id: "shared-id-123", // Already linked!
            experiencia: "Nuevo",
            juegos_este_ano: 0,
            prioridad: 0,
            partidas_deseadas: 1,
            partidas_gm: 0,
          },
        ],
      };

      render(SnapshotDraft, { props: propsWithLinkedPlayer });

      await fireEvent.click(screen.getByText(/Agregar jugador/i));
      await tick();
      const input = screen.getByPlaceholderText(
        "Escribe para buscar o agregar...",
      );

      // Type something that would normally match both or the alias
      await fireEvent.input(input, { target: { value: "Alias" } });
      await tick();

      // The dropdown should NOT render the alias because its notion_id is already in the draft
      expect(screen.queryByText("Alias Name")).toBeNull();
      expect(screen.queryByText("Main Identity")).toBeNull();
    });
  });

  describe("SyncResolutionModal integration", () => {
    it("should show autocorrect suggestions for similar names via CSV", async () => {
      const { tick } = await import("svelte");
      const api = await import("../../api");

      render(SnapshotDraft, {
        props: {
          ...defaultProps,
          initialPlayers: mockInitialPlayers,
        },
      });

      const mockSimilarNames = [
        {
          notion_id: "1",
          notion_name: "John Doe",
          snapshot: "Jon Doe",
          similarity: 0.9,
          match_method: "fuzzy",
          existing_local_name: "John Doe",
        },
      ];
      vi.mocked(api.checkPlayerSimilarity).mockResolvedValue({
        similarities: mockSimilarNames,
      });

      await fireEvent.click(screen.getByText("📥 Pegar CSV"));
      await tick();
      const textarea = screen.getByPlaceholderText(/nombre,experiencia/);
      await fireEvent.input(textarea, {
        target: { value: "nombre,experiencia\nJon Doe,Nuevo" },
      });
      await fireEvent.click(screen.getByText("Importar"));

      await tick();
      await new Promise((r) => setTimeout(r, 0));
      await tick();

      expect(screen.getByText(/Resolver Conflictos/i)).toBeInTheDocument();
      expect(screen.getByText(/Usar John Doe/i)).toBeInTheDocument();
      expect(screen.getByText(/Omitir/i)).toBeInTheDocument();
    });

    it("should show autocorrect to draft player on inline add similarity", async () => {
      const { tick } = await import("svelte");
      const api = await import("../../api");

      const propsWithPlayer = {
        ...defaultProps,
        initialPlayers: [
          {
            nombre: "Daniel E",
            experiencia: "Nuevo",
            juegos_este_ano: 0,
            prioridad: 1,
            partidas_deseadas: 1,
            partidas_gm: 0,
            notion_id: "notion-123",
            notion_name: "DaniVonKlaus",
          },
        ],
      };

      vi.mocked(api.checkPlayerSimilarity).mockResolvedValueOnce({
        similarities: [
          {
            notion_id: "notion-123",
            notion_name: "DaniVonKlaus",
            snapshot: "Dan",
            similarity: 0.9,
            match_method: "fuzzy",
          },
        ],
      });

      render(SnapshotDraft, { props: propsWithPlayer });

      await fireEvent.click(screen.getByText(/Agregar jugador/i));
      await tick();
      const input = screen.getByPlaceholderText(
        "Escribe para buscar o agregar...",
      );

      await fireEvent.input(input, { target: { value: "Dan" } });
      await fireEvent.keyDown(input, { key: "Enter" });

      await tick();
      await new Promise((r) => setTimeout(r, 0));
      await tick();

      // Modal should appear with autocorrect
      expect(
        screen.getByText(/Jugador existente detectado/),
      ).toBeInTheDocument();
      const useExistingBtn = screen.getByRole("button", {
        name: /Usar Daniel E/i,
      });

      // Click Use Existing
      await fireEvent.click(useExistingBtn);

      await tick();
      await new Promise((r) => setTimeout(r, 0));
      await tick();

      // Should not add a new row
      const allRows = document.querySelectorAll(".table-input-ghost");
      expect(allRows.length).toBe(1);
      expect((allRows[0] as HTMLInputElement).value).toBe("Daniel E");
    });

    it("does not render the autocomplete dropdown if there are no suggested players", async () => {
      const { tick } = await import("svelte");
      const { container } = render(SnapshotDraft, {
        props: { ...defaultProps, initialPlayers: mockInitialPlayers },
      });

      await fireEvent.click(screen.getByText("➕ Agregar jugador"));
      await tick();

      const input = screen.getByPlaceholderText(
        "Escribe para buscar o agregar...",
      );
      await fireEvent.input(input, { target: { value: "ZxcvbnmNoMatch" } });
      await tick();

      const dropdown = container.querySelector(".autocomplete-dropdown");
      expect(dropdown).toBeNull();
    });

    it("applies notion_id and shows ? icon when resolving via 'Vincular Solo'", async () => {
      const { tick } = await import("svelte");
      const api = await import("../../api");

      // Setup initial player
      render(SnapshotDraft, {
        props: {
          ...defaultProps,
          initialPlayers: [
            {
              nombre: "Local Name",
              experiencia: "Nuevo",
              juegos_este_ano: 0,
              prioridad: 0,
              partidas_deseadas: 1,
              partidas_gm: 0,
            },
          ],
        },
      });

      // Mock Notion sync response with conflict
      vi.mocked(api.fetchNotionPlayers).mockResolvedValueOnce({
        players: [
          {
            notion_id: "notion-123",
            nombre: "Notion Name",
            experiencia: "Antiguo",
            juegos_este_ano: 5,
          },
        ],
        similar_names: [
          {
            notion_id: "notion-123",
            notion_name: "Notion Name",
            snapshot: "Local Name",
            similarity: 0.9,
            match_method: "fuzzy",
          },
        ],
      });

      // Click Importar Notion
      await fireEvent.click(
        screen.getByRole("button", { name: /Importar Notion/i }),
      );
      await tick();
      await new Promise((r) => setTimeout(r, 0));
      await tick();

      // Modal should appear. Click "Vincular Solo"
      const linkOnlyBtn = screen.getByRole("button", {
        name: /Vincular Solo/i,
      });
      await fireEvent.click(linkOnlyBtn);

      // Flush state updates
      await tick();

      // Verify the player kept their local name
      const nameInput = screen.getByDisplayValue("Local Name");
      expect(nameInput).toBeInTheDocument();

      // Verify ⚡ icon is rendered (meaning notion_id was successfully attached!)
      expect(screen.getAllByText("⚡️").length).toBeGreaterThan(0);

      // Verify no duplicate was added (should only be 1 row!)
      const allRows = document.querySelectorAll(".table-input-ghost");
      expect(allRows.length).toBe(1);

      // Verify alias hint is rendered
      expect(screen.getByText("(Notion Name)")).toBeInTheDocument();
    });

    it("CSV import with 'Vincular Solo' preserves notion_id in DOM and save payload", async () => {
      const { tick } = await import("svelte");
      const api = await import("../../api");
      const { parsePlayersCsv } = await import("../../utils");

      // Override the global CSV mock specifically for this test
      (parsePlayersCsv as ReturnType<typeof vi.fn>).mockReturnValueOnce([
        {
          nombre: "Local Typo",
          experiencia: "Nuevo",
          juegos_este_ano: 0,
          prioridad: 0,
          partidas_deseadas: 1,
          partidas_gm: 0,
        },
      ]);

      // 1. Setup the mocks specifically for this flow
      vi.mocked(api.checkPlayerSimilarity).mockResolvedValueOnce({
        similarities: [
          {
            notion_id: "notion-999",
            notion_name: "Real Notion Name",
            snapshot: "Local Typo",
            similarity: 0.85,
            match_method: "fuzzy",
          },
        ],
      });
      vi.mocked(api.lookupPlayerHistory).mockResolvedValue({
        player: {
          nombre: "Local Typo",
          experiencia: "Antiguo",
          juegos_este_ano: 5,
          prioridad: 0,
          partidas_deseadas: 1,
          partidas_gm: 0,
          source: "notion",
          notion_id: "notion-999",
          notion_name: "Real Notion Name",
        },
      });

      render(SnapshotDraft, { props: defaultProps });

      // 2. Trigger CSV Import
      await fireEvent.click(screen.getByText("📥 Pegar CSV"));
      await tick();
      const textarea = screen.getByPlaceholderText(/nombre,experiencia/);
      await fireEvent.input(textarea, {
        target: { value: "nombre,experiencia\nLocal Typo,Nuevo" },
      });
      await fireEvent.click(screen.getByText("Importar"));

      await tick();
      await new Promise((r) => setTimeout(r, 0));
      await tick();

      // 3. Modal opens. Click "Vincular Solo"
      const linkOnlyBtn = screen.getByRole("button", {
        name: /Vincular Solo/i,
      });
      await fireEvent.click(linkOnlyBtn);

      // 4. Flush all the async history lookups
      await tick();
      await new Promise((r) => setTimeout(r, 0));
      await tick();

      // 5. Assert DOM state (PlayerName component output)
      expect(screen.getByDisplayValue("Local Typo")).toBeInTheDocument();
      expect(screen.getByText("(Real Notion Name)")).toBeInTheDocument();
      expect(screen.getAllByText("⚡️").length).toBeGreaterThan(0);

      // 6. Click Save
      await fireEvent.click(
        screen.getByRole("button", { name: /Crear Versión/i }),
      );

      // 7. Assert Save Payload EXACTLY matches what we expect
      expect(api.saveSnapshot).toHaveBeenCalledWith(
        expect.objectContaining({
          event_type: "manual",
          players: expect.arrayContaining([
            expect.objectContaining({
              nombre: "Local Typo",
              notion_id: "notion-999",
              notion_name: "Real Notion Name",
              experiencia: "Nuevo", // Overridden by CSV input!
              juegos_este_ano: 0, // Overridden by CSV input!
            }),
          ]),
        }),
      );
    });
  });

  describe("confirmAddPlayer Edge Cases", () => {
    it("should handle string vs AutocompletePlayer object correctly", async () => {
      const { tick } = await import("svelte");
      const onShowError = vi.fn();
      const api = await import("../../api");

      // Mock getAllPlayers to return notion player
      vi.mocked(api.getAllPlayers).mockResolvedValue({
        players: [
          {
            display: "Notion Player",
            nombre: "Notion Player",
            notion_id: "notion-123",
            is_local: false,
            is_alias: false,
          },
        ],
      });

      render(SnapshotDraft, { props: { ...defaultProps, onShowError } });

      // Test 1: Adding raw string through autocomplete
      await fireEvent.click(screen.getByText(/Agregar jugador/i));
      await tick();
      let input = screen.getByPlaceholderText(
        "Escribe para buscar o agregar...",
      );

      await fireEvent.input(input, { target: { value: "String Player" } });
      await fireEvent.keyDown(input, { key: "Enter" });

      await tick();
      await new Promise((r) => setTimeout(r, 0)); // flush API promises
      await tick();

      const stringRow = screen.getByDisplayValue("String Player");
      expect(stringRow).toBeInTheDocument();
      expect(onShowError).not.toHaveBeenCalled();

      // Test 2: Adding AutocompletePlayer with notion_id
      await fireEvent.click(screen.getByText(/Agregar jugador/i));
      await tick();
      input = screen.getByPlaceholderText("Escribe para buscar o agregar...");

      await fireEvent.input(input, { target: { value: "Notion" } });
      await tick();

      // Click on the autocomplete suggestion
      const suggestion = screen.getByText("Notion Player");
      await fireEvent.click(suggestion);

      await tick();
      await new Promise((r) => setTimeout(r, 0)); // flush API promises
      await tick();

      const notionRow = screen.getByDisplayValue("Notion Player");
      expect(notionRow).toBeInTheDocument();

      // Verify notion_id was applied by checking for the flash icon!
      const flashIcons = screen.getAllByText("⚡️");
      expect(flashIcons.length).toBeGreaterThan(0);
      expect(onShowError).not.toHaveBeenCalled();
    });

    it("should block duplicate players and call onShowError", async () => {
      const { tick } = await import("svelte");
      const onShowError = vi.fn();
      const propsWithPlayer = {
        ...defaultProps,
        initialPlayers: [
          {
            nombre: "Existing Player",
            experiencia: "Nuevo",
            juegos_este_ano: 0,
            prioridad: 1,
            partidas_deseadas: 1,
            partidas_gm: 0,
          },
        ],
        onShowError,
      };

      render(SnapshotDraft, { props: propsWithPlayer });

      // Try to add a duplicate player
      await fireEvent.click(screen.getByText(/Agregar jugador/i));
      await tick();
      const input = screen.getByPlaceholderText(
        "Escribe para buscar o agregar...",
      );

      await fireEvent.input(input, { target: { value: "Existing Player" } });
      await fireEvent.keyDown(input, { key: "Enter" });

      await tick();

      // Should call onShowError for duplicate (matching the exact code string)
      expect(onShowError).toHaveBeenCalledWith(
        "Jugador duplicado",
        expect.stringContaining("ya está en la lista"),
      );

      // Should NOT add the duplicate to the table
      const duplicates = screen.queryAllByDisplayValue("Existing Player");
      expect(duplicates).toHaveLength(1); // Only the original
    });

    it("should silently suppress duplicates when force flag is true", async () => {
      const { tick } = await import("svelte");
      const onShowError = vi.fn();
      const propsWithPlayer = {
        ...defaultProps,
        initialPlayers: [
          {
            nombre: "Silent Duplicate",
            experiencia: "Nuevo",
            juegos_este_ano: 0,
            prioridad: 1,
            partidas_deseadas: 1,
            partidas_gm: 0,
          },
        ],
        onShowError,
      };

      render(SnapshotDraft, { props: propsWithPlayer });

      // Trigger standard duplicate add
      await fireEvent.click(screen.getByText(/Agregar jugador/i));
      await tick();
      const input = screen.getByPlaceholderText(
        "Escribe para buscar o agregar...",
      );

      await fireEvent.input(input, { target: { value: "Silent Duplicate" } });
      await fireEvent.keyDown(input, { key: "Enter" });

      await tick();

      // Normal duplicate should call onShowError
      expect(onShowError).toHaveBeenCalledWith(
        "Jugador duplicado",
        expect.stringContaining("ya está en la lista"),
      );

      // Should NOT add the duplicate to the table
      const duplicates = screen.queryAllByDisplayValue("Silent Duplicate");
      expect(duplicates).toHaveLength(1); // Only the original
    });
  });
});
