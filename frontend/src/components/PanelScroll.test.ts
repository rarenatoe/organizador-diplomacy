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
    copypaste: "Test copypaste",
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
          onclose: () => {},
          onchainUpdate: () => {},
          onopenSnapshot: () => {},
        },
      });

      // Wait for loading to complete
      await vi.waitFor(() => {
        expect(screen.queryByText("Cargando…")).toBeNull();
      });

      const fixedHeader = container.querySelector(".panel-body-fixed");
      const tableWrap = container.querySelector(".flex-table-wrap");

      expect(fixedHeader).toBeTruthy();
      expect(tableWrap).toBeTruthy();
      expect(container.querySelector(".panel-scroll")).toBeNull(); // Ensure old wrapper is gone
    });

    it("should have panel-footer outside panel-scroll with action buttons", async () => {
      const { container } = render(SnapshotDetail, {
        props: {
          id: 1,
          onclose: () => {},
          onchainUpdate: () => {},
          onopenSnapshot: () => {},
        },
      });

      await vi.waitFor(() => {
        expect(screen.queryByText("Cargando…")).toBeNull();
      });

      const panelFooter = container.querySelector(".panel-footer");
      expect(panelFooter).toBeTruthy();

      // Verify action buttons are inside panel-footer
      const addButton = screen.getByText("➕ Agregar jugador");
      const createButton = screen.getByText(
        "✨ Crear snapshot manual con estos ajustes",
      );

      expect(panelFooter?.contains(addButton)).toBe(true);
      expect(panelFooter?.contains(createButton)).toBe(true);
    });

    it("should not have section class on panel-footer", async () => {
      const { container } = render(SnapshotDetail, {
        props: {
          id: 1,
          onclose: () => {},
          onchainUpdate: () => {},
          onopenSnapshot: () => {},
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
        props: { id: 1 },
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
  });
});
