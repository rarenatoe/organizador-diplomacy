// ── Global State Management ───────────────────────────────────────────────────
// Uses plain JavaScript objects for state to support testing.
// Svelte components access this state reactively via $state runes.

import { ChainResponse } from "./generated-api";

// ── State container ───────────────────────────────────────────────────────────

interface AppState {
  snapshotCount: number;
  chainData: ChainResponse | undefined;
  activeNodeId: number | null;
}

const state = $state<AppState>({
  snapshotCount: -1, // -1 means loading/unknown state
  chainData: undefined,
  activeNodeId: null,
});

// ── Convenience getters/setters ───────────────────────────────────────────────

export function setSnapshotCount(count: number): void {
  state.snapshotCount = count;
}

export function setChainData(data: ChainResponse | undefined): void {
  state.chainData = data;
}

export function setActiveNodeId(id: number | null): void {
  state.activeNodeId = id;
}

export function getChainData(): ChainResponse | undefined {
  return state.chainData;
}

export function getActiveNodeId(): number | null {
  return state.activeNodeId;
}
