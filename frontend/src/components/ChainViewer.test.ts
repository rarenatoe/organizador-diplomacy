import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";

// Mock the API module
vi.mock("../api", () => ({
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
import { fetchChain } from "../api";

describe("ChainViewer.svelte - Empty State Integration", () => {
  const mockProps = {
    onOpenSnapshot: vi.fn(),
    onOpenGame: vi.fn(),
    onDeleteSnapshot: vi.fn(),
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
