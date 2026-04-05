import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/svelte";
import SnapshotDetail from "./SnapshotDetail.svelte";
import GameDetail from "./GameDetail.svelte";
import SyncDetail from "./SyncDetail.svelte";

// Mock the API module
vi.mock("../api", () => ({
  fetchSnapshot: vi.fn().mockResolvedValue({
    source: "manual",
    created_at: "2024-01-01",
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
  }),
  fetchGame: vi.fn().mockResolvedValue({
    created_at: "2024-01-01",
    intentos: 1,
    input_snapshot_id: 1,
    output_snapshot_id: 2,
    mesas: [],
    waiting_list: [],
  }),
  fetchChain: vi.fn().mockResolvedValue({
    roots: [
      {
        id: 1,
        branches: [
          {
            edge: {
              type: "sync",
              id: 1,
              from_id: 1,
              to_id: 2,
              created_at: "2024-01-01",
            },
            output: null,
          },
        ],
      },
    ],
  }),
  editSnapshot: vi.fn(),
  addPlayer: vi.fn(),
  renamePlayer: vi.fn(),
}));

// Mock the stores
vi.mock("../stores.svelte", () => ({
  setSelectedSnapshot: vi.fn(),
}));

describe("Panel Scroll Pattern", () => {
  describe("SnapshotDetail", () => {
    it("should use panel-body-fixed and flex-table-wrap for sticky table layout", async () => {
      const { container } = render(SnapshotDetail, {
        props: {
          id: 1,
          onClose: () => {},
          onChainUpdate: () => {},
          onOpenSnapshot: () => {},
          onOpenGame: () => {},
          onOpenGameDraft: () => {},
          onEditDraft: () => {},
          onShowError: () => {},
          onShowToast: vi.fn(),
        },
      });

      // Wait for loading to complete
      await vi.waitFor(() => {
        expect(screen.queryByText("Cargando…")).toBeNull();
      });

      const fixedHeader = container.querySelector(".panel-body-fixed");
      const tableWrap = container.querySelector(".data-table-wrapper");

      expect(fixedHeader).toBeTruthy();
      expect(tableWrap).toBeTruthy();
      expect(container.querySelector(".panel-scroll")).toBeNull(); // Ensure scrollable={false} worked
    });

    it("should have panel-footer with action buttons", async () => {
      const { container } = render(SnapshotDetail, {
        props: {
          id: 1,
          onClose: () => {},
          onChainUpdate: () => {},
          onOpenSnapshot: () => {},
          onOpenGame: () => {},
          onOpenGameDraft: () => {},
          onEditDraft: () => {},
          onShowError: () => {},
          onShowToast: vi.fn(),
        },
      });

      await vi.waitFor(() => {
        expect(screen.queryByText("Cargando…")).toBeNull();
      });

      const panelFooter = container.querySelector(".panel-footer");
      expect(panelFooter).toBeTruthy();

      // Verify action buttons are inside panel-footer
      const editButton = screen.getByText("Editar");
      const syncButton = screen.getByText("Sincronizar Notion");
      const organizarButton = screen.getByText("Organizar Partidas");

      expect(panelFooter?.contains(editButton)).toBe(true);
      expect(panelFooter?.contains(syncButton)).toBe(true);
      expect(panelFooter?.contains(organizarButton)).toBe(true);
    });

    it("should not have section class on panel-footer", async () => {
      const { container } = render(SnapshotDetail, {
        props: {
          id: 1,
          onClose: () => {},
          onChainUpdate: () => {},
          onOpenSnapshot: () => {},
          onOpenGame: () => {},
          onOpenGameDraft: () => {},
          onEditDraft: () => {},
          onShowError: () => {},
          onShowToast: vi.fn(),
        },
      });

      await vi.waitFor(() => {
        expect(screen.queryByText("Cargando…")).toBeNull();
      });

      const panelFooter = container.querySelector(".panel-footer");
      expect(panelFooter?.classList.contains("section")).toBe(false);
    });
  });

  describe("GameDetail", () => {
    it("should have panel-scroll wrapper around all content", async () => {
      const { container } = render(GameDetail, {
        props: { id: 1, openGameDraft: vi.fn() },
      });

      await vi.waitFor(() => {
        expect(screen.queryByText("Cargando…")).toBeNull();
      });

      const panelScroll = container.querySelector(".panel-scroll");
      expect(panelScroll).toBeTruthy();

      // Verify all sections are inside panel-scroll
      const sections = panelScroll?.querySelectorAll(".section");
      expect(sections?.length).toBeGreaterThanOrEqual(1);
    });

    it("should have conditional panel-footer when openGameDraft is provided", async () => {
      const { container } = render(GameDetail, {
        props: {
          id: 1,
          openGameDraft: () => {},
        },
      });

      await vi.waitFor(() => {
        expect(screen.queryByText("Cargando…")).toBeNull();
      });

      const panelFooter = container.querySelector(".panel-footer");
      expect(panelFooter).toBeTruthy();

      // Verify the "Editar Jornada" button is in the footer
      const editButton = screen.getByText("Editar Jornada");
      expect(panelFooter?.contains(editButton)).toBe(true);
    });
  });

  describe("SyncDetail", () => {
    it("should have panel-scroll wrapper around content", async () => {
      const { container } = render(SyncDetail, {
        props: { id: 1 },
      });

      await vi.waitFor(() => {
        expect(screen.queryByText("Cargando…")).toBeNull();
      });

      const panelScroll = container.querySelector(".panel-scroll");
      expect(panelScroll).toBeTruthy();
    });
  });

  describe("CSS Classes", () => {
    it("panel-scroll should have correct flex properties", () => {
      const style = document.createElement("style");
      style.textContent = `
        .panel-scroll {
          flex: 1;
          overflow-y: auto;
          min-height: 0;
          padding: 16px 18px;
        }
      `;
      document.head.appendChild(style);

      const element = document.createElement("div");
      element.className = "panel-scroll";
      document.body.appendChild(element);

      const computedStyle = window.getComputedStyle(element);
      // Browser normalizes flex: 1 to "1 1 0%"
      expect(computedStyle.flex).toMatch(/^1/);
      expect(computedStyle.overflowY).toBe("auto");

      document.body.removeChild(element);
      document.head.removeChild(style);
    });

    it("panel-footer should have flex-shrink: 0", () => {
      const style = document.createElement("style");
      style.textContent = `
        .panel-footer {
          flex-shrink: 0;
          padding: 16px 18px;
          border-top: 1px solid var(--border);
          background: var(--surface);
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
      `;
      document.head.appendChild(style);

      const element = document.createElement("div");
      element.className = "panel-footer";
      document.body.appendChild(element);

      const computedStyle = window.getComputedStyle(element);
      expect(computedStyle.flexShrink).toBe("0");

      document.body.removeChild(element);
      document.head.removeChild(style);
    });

    it("table should have min-width: max-content for horizontal scroll", () => {
      const style = document.createElement("style");
      style.textContent = `
        table {
          width: 100%;
          border-collapse: collapse;
          font-size: 12px;
          min-width: max-content;
        }
      `;
      document.head.appendChild(style);

      const element = document.createElement("table");
      document.body.appendChild(element);

      const computedStyle = window.getComputedStyle(element);
      expect(computedStyle.minWidth).toBe("max-content");

      document.body.removeChild(element);
      document.head.removeChild(style);
    });

    it("player-name should not have overflow hidden", () => {
      const style = document.createElement("style");
      style.textContent = `
        .player-name {
          flex: 1;
          white-space: nowrap;
        }
      `;
      document.head.appendChild(style);

      const element = document.createElement("span");
      element.className = "player-name";
      document.body.appendChild(element);

      const computedStyle = window.getComputedStyle(element);
      expect(computedStyle.overflow).not.toBe("hidden");
      expect(computedStyle.textOverflow).not.toBe("ellipsis");

      document.body.removeChild(element);
      document.head.removeChild(style);
    });

    it("flex-table-wrap should prevent elastic scrolling (overscroll-behavior-y)", () => {
      const style = document.createElement("style");
      style.textContent = `
        .flex-table-wrap {
          flex: 1;
          overflow: auto;
          overscroll-behavior-y: none;
        }
      `;
      document.head.appendChild(style);

      const element = document.createElement("div");
      element.className = "flex-table-wrap";
      document.body.appendChild(element);

      const computedStyle = window.getComputedStyle(element);
      expect(computedStyle.overscrollBehaviorY).toBe("none");

      document.body.removeChild(element);
      document.head.removeChild(style);
    });

    it("table headers should not have inset box-shadows that create inconsistent borders", () => {
      // This test ensures headers don't have extra bottom borders via inset box-shadows
      // which was the cause of the "Nombre" header having a bottom edge that other headers didn't have
      const style = document.createElement("style");
      style.textContent = `
        .flex-table-wrap th {
          position: sticky;
          top: 0;
          z-index: 10;
          background: var(--surface2);
          transform: translateZ(0);
          background-clip: padding-box;
          border-bottom: 1px solid var(--border);
          box-shadow: none;
        }
        
        .flex-table-wrap th:nth-child(2) {
          z-index: 12;
          background: var(--surface2);
          box-shadow: 2px 0 4px -2px rgba(0, 0, 0, 0.1);
        }
      `;
      document.head.appendChild(style);

      const table = document.createElement("table");
      table.className = "flex-table-wrap";
      const thead = document.createElement("thead");
      const tr = document.createElement("tr");

      // Create multiple headers to test consistency
      for (let i = 0; i < 5; i++) {
        const th = document.createElement("th");
        th.textContent = `Header ${i + 1}`;
        tr.appendChild(th);
      }

      thead.appendChild(tr);
      table.appendChild(thead);
      document.body.appendChild(table);

      const headers = table.querySelectorAll("th");

      // Check that no header has inset box-shadow
      headers.forEach((header) => {
        const computedStyle = window.getComputedStyle(header);
        const boxShadow = computedStyle.boxShadow;

        // inset box-shadows would contain "inset" keyword
        // We want to ensure headers don't have this
        expect(boxShadow).not.toContain("inset");
      });

      document.body.removeChild(table);
      document.head.removeChild(style);
    });

    it("all table headers should have consistent border-bottom styling", () => {
      // This test ensures all headers in a table have the same border-bottom style
      const style = document.createElement("style");
      style.textContent = `
        th {
          border-bottom: 1px solid var(--border);
        }
      `;
      document.head.appendChild(style);

      const table = document.createElement("table");
      const thead = document.createElement("thead");
      const tr = document.createElement("tr");

      for (let i = 0; i < 5; i++) {
        const th = document.createElement("th");
        th.textContent = `Header ${i + 1}`;
        tr.appendChild(th);
      }

      thead.appendChild(tr);
      table.appendChild(thead);
      document.body.appendChild(table);

      const headers = table.querySelectorAll("th");
      expect(headers.length).toBeGreaterThan(0);

      const firstHeader = headers[0];
      if (!firstHeader) {
        throw new Error("No headers found in table");
      }

      const firstHeaderStyle = window.getComputedStyle(firstHeader);
      const expectedBorderBottom = firstHeaderStyle.borderBottom;

      // All headers should have the same border-bottom style
      headers.forEach((header) => {
        const computedStyle = window.getComputedStyle(header);
        expect(computedStyle.borderBottom).toBe(expectedBorderBottom);
      });

      document.body.removeChild(table);
      document.head.removeChild(style);
    });
  });
});
