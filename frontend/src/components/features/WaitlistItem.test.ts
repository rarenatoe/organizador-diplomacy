import { render, screen } from "@testing-library/svelte";
import * as generatedApi from "../../generated-api";
import { mockApiSuccess } from "../../tests/mockHelpers";
import { createMockDraftPlayer } from "../../tests/fixtures";
import type { GameDetailResponse } from "../../generated-api";
import GameDetail from "./GameDetail.svelte";

const apiGameSpy = vi.spyOn(generatedApi, "apiGame");

const gameDetailResponse: GameDetailResponse = {
  id: 1,
  created_at: "2024-01-01T00:00:00Z",
  intentos: 1,
  input_snapshot_id: 10,
  output_snapshot_id: 20,
  mesas: [],
  waiting_list: [
    createMockDraftPlayer({ nombre: "Charlie", cupos_faltantes: 1 }),
  ],
};

it("enforces structural regression guard: uses centralized Waitlist component", async () => {
  apiGameSpy.mockResolvedValue(mockApiSuccess(gameDetailResponse));

  const { container } = render(GameDetail, {
    props: {
      id: 1,
      onOpenGameDraft: vi.fn(),
    },
  });

  await screen.findByText("Lista de espera");

  // Verify it uses the waitlist-container abstraction to govern spacing
  // If someone reverts to the old {#each} loop without the container, this test will fail
  expect(container.querySelector(".waitlist-container")).toBeInTheDocument();
});
