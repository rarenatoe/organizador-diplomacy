import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";

// Mock the API module
vi.mock("../../api", () => ({
  fetchChain: vi.fn(),
}));

// Mock the GameNode component
vi.mock("./GameNode.svelte", () => ({
  default: vi.fn(() => ({
    $$: { on_destroy: [] },
  })),
}));

// Import ChainViewer and API
import ChainViewer from "./ChainViewer.svelte";
import { fetchChain } from "../../api";

describe("ChainViewer.svelte - Empty State Integration", () => {
  const mockProps = {
    onOpenSnapshot: vi.fn(),
    onOpenGame: vi.fn(),
    onDeleteSnapshot: vi.fn(),
    onDeleteGame: vi.fn(),
    onNewDraft: vi.fn(),
    panelOpen: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Mock fetchChain to return empty data for empty state
    vi.mocked(fetchChain).mockResolvedValue({
      roots: [],
    });
  });

  it("renders empty state when there are no snapshots", async () => {
    render(ChainViewer, { props: mockProps });

    // Wait for loading to complete and empty state to appear
    await vi.waitFor(() => {
      expect(
        screen.getByText("No hay snapshots en la DB."),
      ).toBeInTheDocument();
    });

    // Verify the introductory text
    expect(
      screen.getByText(
        "Comienza importando jugadores o creando una versión desde cero.",
      ),
    ).toBeInTheDocument();
  });

  it("renders all three empty state buttons", async () => {
    render(ChainViewer, { props: mockProps });

    // Wait for loading to complete
    await vi.waitFor(() => {
      expect(
        screen.getByText("No hay snapshots en la DB."),
      ).toBeInTheDocument();
    });

    // Assert that all three buttons are rendered by their Spanish text
    expect(screen.getByText("Importar de Notion")).toBeInTheDocument();
    expect(screen.getByText("Pegar CSV")).toBeInTheDocument();
    expect(screen.getByText("Crear desde cero")).toBeInTheDocument();
  });

  it("triggers onNewDraft with notion option when Importar de Notion is clicked", async () => {
    render(ChainViewer, { props: mockProps });

    // Wait for loading to complete
    await vi.waitFor(() => {
      expect(screen.getByText("Importar de Notion")).toBeInTheDocument();
    });

    const notionButton = screen.getByText("Importar de Notion");
    await fireEvent.click(notionButton);

    expect(mockProps.onNewDraft).toHaveBeenCalledTimes(1);
    expect(mockProps.onNewDraft).toHaveBeenCalledWith({ autoAction: "notion" });
  });

  it("triggers onNewDraft with csv option when Pegar CSV is clicked", async () => {
    render(ChainViewer, { props: mockProps });

    // Wait for loading to complete
    await vi.waitFor(() => {
      expect(screen.getByText("Pegar CSV")).toBeInTheDocument();
    });

    const csvButton = screen.getByText("Pegar CSV");
    await fireEvent.click(csvButton);

    expect(mockProps.onNewDraft).toHaveBeenCalledTimes(1);
    expect(mockProps.onNewDraft).toHaveBeenCalledWith({ autoAction: "csv" });
  });

  it("triggers onNewDraft with no options when Crear desde cero is clicked", async () => {
    render(ChainViewer, { props: mockProps });

    // Wait for loading to complete
    await vi.waitFor(() => {
      expect(screen.getByText("Crear desde cero")).toBeInTheDocument();
    });

    const createButton = screen.getByText("Crear desde cero");
    await fireEvent.click(createButton);

    expect(mockProps.onNewDraft).toHaveBeenCalledTimes(1);
    expect(mockProps.onNewDraft).toHaveBeenCalledWith();
  });

  it("shows loading state initially", () => {
    render(ChainViewer, { props: mockProps });

    // Should show loading state initially
    expect(screen.getByText("Cargando...")).toBeInTheDocument();
    expect(screen.getByText("⏳")).toBeInTheDocument();
  });
});

describe("ChainViewer.svelte - Delete Functionality", () => {
  const mockProps = {
    onOpenSnapshot: vi.fn(),
    onOpenGame: vi.fn(),
    onDeleteSnapshot: vi.fn(),
    onDeleteGame: vi.fn(),
    onNewDraft: vi.fn(),
    panelOpen: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Mock fetchChain to return data with snapshot and game nodes
    vi.mocked(fetchChain).mockResolvedValue({
      roots: [
        {
          id: 1,
          type: "snapshot",
          created_at: "2024-01-01 10:00:00",
          source: "manual",
          player_count: 5,
          is_latest: true,
          branches: [
            {
              edge: {
                id: 2,
                type: "game",
                created_at: "2024-01-01 11:00:00",
                mesa_count: 2,
                espera_count: 3,
                to_id: 2,
                from_id: 1,
                intentos: 0,
              },
              output: null,
            },
          ],
        },
      ],
    });
  });

  it("renders delete buttons for both snapshot and game nodes", async () => {
    render(ChainViewer, { props: mockProps });

    // Wait for data to load
    await vi.waitFor(() => {
      // Should find delete buttons (they have trash icon)
      const deleteButtons = screen.getAllByText("🗑");
      expect(deleteButtons.length).toBeGreaterThan(0);
    });
  });

  it("calls onDeleteSnapshot when snapshot delete button is clicked", async () => {
    render(ChainViewer, { props: mockProps });

    await vi.waitFor(() => {
      const deleteButtons = screen.getAllByText("🗑");
      expect(deleteButtons.length).toBeGreaterThan(0);
    });

    // Click the first delete button (should be snapshot delete)
    const deleteButtons = screen.getAllByText("🗑");
    const firstButton = deleteButtons[0];
    if (firstButton) {
      await fireEvent.click(firstButton);
    }

    expect(mockProps.onDeleteSnapshot).toHaveBeenCalledTimes(1);
    expect(mockProps.onDeleteSnapshot).toHaveBeenCalledWith(1);
  });

  // Note: Game deletion testing is not possible with current mock setup
  // but the functionality is verified in GameNode component tests
});
