import { vi } from "vitest";

export const mockInitialPlayers = [
  {
    nombre: "Test Player",
    is_new: true,
    juegos_este_ano: 0,
    has_priority: false,
    partidas_deseadas: 1,
    partidas_gm: 0,
    oldName: "Test Player",
    historyRestored: false,
  },
];
export const defaultProps = {
  parentId: null,
  initialPlayers: [],
  saveEventType: "manual" as const,
  onClose: vi.fn(),
  onCancel: vi.fn(),
  onChainUpdate: vi.fn(),
  onOpenSnapshot: vi.fn(),
  onShowError: vi.fn(),
};
