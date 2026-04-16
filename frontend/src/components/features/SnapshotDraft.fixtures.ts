import { vi } from "vitest";

export const mockInitialPlayers = [
  {
    nombre: "Test Player",
    experiencia: "Nuevo",
    juegos_este_ano: 0,
    has_priority: false,
    partidas_deseadas: 1,
    partidas_gm: 0,
    original_nombre: "Test Player",
    historyRestored: false,
  },
];
export const defaultProps = {
  parentId: null,
  initialPlayers: [],
  defaultEventType: "manual" as const,
  onClose: vi.fn(),
  onCancel: vi.fn(),
  onChainUpdate: vi.fn(),
  onOpenSnapshot: vi.fn(),
  onShowError: vi.fn(),
};
