import { describe, it, expect, vi, beforeEach } from "vitest";
import "@testing-library/jest-dom";
import { showRenameDialog, showAddPlayerDialog } from "./panels";

// Mock the dependencies
vi.mock("./chain", () => ({
  esc: (s: string) => s,
  loadChain: vi.fn(),
}));

vi.mock("./clipboard", () => ({
  reg: vi.fn(() => "mock-ck"),
}));

vi.mock("./selection", () => ({
  getSelectedSnapshot: vi.fn(() => null),
  setSelectedSnapshot: vi.fn(),
  deselectSnapshot: vi.fn(),
}));

// Mock fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe("panels", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset DOM
    document.body.innerHTML = "";
  });

  describe("showRenameDialog", () => {
    it("should call rename API and reload snapshot on success", async () => {
      const mockPrompt = vi.fn().mockReturnValue("NewName");
      global.prompt = mockPrompt;

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      });

      await showRenameDialog("OldName", 1);

      expect(mockFetch).toHaveBeenCalledWith("/api/player/rename", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ old_name: "OldName", new_name: "NewName" }),
      });
    });

    it("should show error alert when rename fails", async () => {
      const mockPrompt = vi.fn().mockReturnValue("NewName");
      const mockAlert = vi.fn();
      global.prompt = mockPrompt;
      global.alert = mockAlert;

      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ error: "Name already exists" }),
      });

      await showRenameDialog("OldName", 1);

      expect(mockAlert).toHaveBeenCalledWith("Error: Name already exists");
    });

    it("should not call API when user cancels prompt", async () => {
      const mockPrompt = vi.fn().mockReturnValue(null);
      global.prompt = mockPrompt;

      await showRenameDialog("OldName", 1);

      expect(mockFetch).not.toHaveBeenCalled();
    });

    it("should not call API when new name equals old name", async () => {
      const mockPrompt = vi.fn().mockReturnValue("OldName");
      global.prompt = mockPrompt;

      await showRenameDialog("OldName", 1);

      expect(mockFetch).not.toHaveBeenCalled();
    });
  });

  describe("showAddPlayerDialog", () => {
    it("should call add player API and reload snapshot on success", async () => {
      const mockPrompt = vi
        .fn()
        .mockReturnValueOnce("NewPlayer")
        .mockReturnValueOnce("Nuevo")
        .mockReturnValueOnce("0");
      global.prompt = mockPrompt;

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ player_id: 123 }),
      });

      await showAddPlayerDialog(1);

      expect(mockFetch).toHaveBeenCalledWith("/api/snapshot/1/add-player", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nombre: "NewPlayer",
          experiencia: "Nuevo",
          juegos_este_ano: 0,
          prioridad: 0,
          partidas_deseadas: 1,
          partidas_gm: 0,
        }),
      });
    });

    it("should show error alert when add player fails", async () => {
      const mockPrompt = vi
        .fn()
        .mockReturnValueOnce("NewPlayer")
        .mockReturnValueOnce("Nuevo")
        .mockReturnValueOnce("0");
      const mockAlert = vi.fn();
      global.prompt = mockPrompt;
      global.alert = mockAlert;

      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ error: "Player already exists" }),
      });

      await showAddPlayerDialog(1);

      expect(mockAlert).toHaveBeenCalledWith("Error: Player already exists");
    });

    it("should not call API when user cancels name prompt", async () => {
      const mockPrompt = vi.fn().mockReturnValue(null);
      global.prompt = mockPrompt;

      await showAddPlayerDialog(1);

      expect(mockFetch).not.toHaveBeenCalled();
    });
  });
});
