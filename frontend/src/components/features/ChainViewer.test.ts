import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";

// Import ChainViewer and API
import ChainViewer from "./ChainViewer.svelte";
import * as generatedApi from "../../generated-api";
import { mockApiSuccess } from "../../tests/mockHelpers";

const apiChainSpy = vi.spyOn(generatedApi, "apiChain");

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
    // Mock apiChain to return empty data for empty state
    apiChainSpy.mockResolvedValue(
      mockApiSuccess({
        roots: [],
      }),
    );
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
    apiChainSpy.mockResolvedValue(
      mockApiSuccess({
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
      }),
    );
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
  // but the functionality is verified in BaseNode component tests
});

describe("ChainViewer.svelte - Layout Regression Guards", () => {
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
    apiChainSpy.mockResolvedValue(
      mockApiSuccess({
        roots: [],
      }),
    );
  });

  it("renders multiple root snapshots in separate chain lanes", async () => {
    apiChainSpy.mockResolvedValue(
      mockApiSuccess({
        roots: [
          {
            id: 1,
            type: "snapshot",
            created_at: "2024-01-01 10:00:00",
            source: "manual",
            player_count: 5,
            is_latest: false,
            branches: [],
          },
          {
            id: 2,
            type: "snapshot",
            created_at: "2024-01-02 11:00:00",
            source: "notion_sync",
            player_count: 7,
            is_latest: true,
            branches: [],
          },
          {
            id: 3,
            type: "snapshot",
            created_at: "2024-01-03 12:00:00",
            source: "manual",
            player_count: 4,
            is_latest: false,
            branches: [],
          },
        ],
      }),
    );

    render(ChainViewer, { props: mockProps });

    // Wait for data to load
    await vi.waitFor(() => {
      expect(screen.getByText("Snapshot #1")).toBeInTheDocument();
      expect(screen.getByText("Snapshot #2")).toBeInTheDocument();
      expect(screen.getByText("Snapshot #3")).toBeInTheDocument();
    });

    // Verify that each root snapshot is wrapped in its own chain-lane container
    const chainLanes = screen.getAllByTestId("chain-lane");
    expect(chainLanes).toHaveLength(3);

    // Verify each chain lane contains the expected snapshot
    expect(chainLanes[0]).toContainElement(screen.getByText("Snapshot #1"));
    expect(chainLanes[1]).toContainElement(screen.getByText("Snapshot #2"));
    expect(chainLanes[2]).toContainElement(screen.getByText("Snapshot #3"));
  });

  it("renders single root snapshot in one chain lane", async () => {
    // Mock with single snapshot
    apiChainSpy.mockResolvedValue(
      mockApiSuccess({
        roots: [
          {
            id: 1,
            type: "snapshot",
            created_at: "2024-01-01 10:00:00",
            source: "manual",
            player_count: 5,
            is_latest: true,
            branches: [],
          },
        ],
      }),
    );

    render(ChainViewer, { props: mockProps });

    await vi.waitFor(() => {
      expect(screen.getByText("Snapshot #1")).toBeInTheDocument();
    });

    // Verify there's exactly one chain lane for the single root
    const chainLanes = screen.getAllByTestId("chain-lane");
    expect(chainLanes).toHaveLength(1);

    // Verify the chain lane contains the snapshot
    expect(chainLanes[0]).toContainElement(screen.getByText("Snapshot #1"));
  });

  it("renders root nodes and their branches within a single chain lane without recursive wrapping", async () => {
    apiChainSpy.mockResolvedValue(
      mockApiSuccess({
        roots: [
          {
            id: 1,
            type: "snapshot",
            created_at: "2024-01-01 10:00:00",
            source: "manual",
            player_count: 5,
            is_latest: false,
            branches: [
              {
                edge: {
                  id: 1,
                  type: "edit",
                  created_at: "2024-01-01 10:30:00",
                  to_id: 2,
                  from_id: 1,
                },
                output: {
                  id: 2,
                  type: "snapshot",
                  created_at: "2024-01-01 11:00:00",
                  source: "manual",
                  player_count: 5,
                  is_latest: true,
                  branches: [],
                },
              },
            ],
          },
        ],
      }),
    );

    render(ChainViewer, { props: mockProps });

    // Wait for data to load
    await vi.waitFor(() => {
      expect(screen.getByText("Snapshot #1")).toBeInTheDocument();
      expect(screen.getByText("Snapshot #2")).toBeInTheDocument();
    });

    // Verify there is exactly ONE chain-lane, proving children aren't wrapped in their own lanes
    const chainLanes = screen.getAllByTestId("chain-lane");
    expect(chainLanes).toHaveLength(1);

    // Verify the single chain lane contains BOTH the root and the child snapshot
    expect(chainLanes[0]).toContainElement(screen.getByText("Snapshot #1"));
    expect(chainLanes[0]).toContainElement(screen.getByText("Snapshot #2"));
  });
});
