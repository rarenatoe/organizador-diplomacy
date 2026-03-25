// ── Global State Management ───────────────────────────────────────────────────
// Uses plain JavaScript objects for state to support testing.
// Svelte components access this state reactively via $state runes.

import type { ChainData } from "./types";

// ── State container ───────────────────────────────────────────────────────────

interface AppState {
  snapshotCount: number;
  chainData: ChainData | null;
  activeNodeId: number | null;
}

const state = $state<AppState>({
  snapshotCount: -1, // -1 means loading/unknown state
  chainData: null,
  activeNodeId: null,
});

// ── Convenience getters/setters ───────────────────────────────────────────────

export function setSnapshotCount(count: number): void {
  state.snapshotCount = count;
}

export function setChainData(data: ChainData): void {
  state.chainData = data;
}

export function setActiveNodeId(id: number | null): void {
  state.activeNodeId = id;
}

export function getChainData(): ChainData | null {
  return state.chainData;
}

export function getActiveNodeId(): number | null {
  return state.activeNodeId;
}
