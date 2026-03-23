// ── Global State Management ───────────────────────────────────────────────────
// Uses plain JavaScript objects for state to support testing.
// Svelte components access this state reactively via $state runes.

import type { ChainData } from "./types";

// ── State container ───────────────────────────────────────────────────────────

interface AppState {
  selectedSnapshot: number | null;
  snapshotCount: number;
  chainData: ChainData | null;
  activeNodeId: string | null;
}

const state: AppState = {
  selectedSnapshot: null,
  snapshotCount: 0,
  chainData: null,
  activeNodeId: null,
};

// ── Convenience getters/setters ───────────────────────────────────────────────

export function getSelectedSnapshot(): number | null {
  return state.selectedSnapshot;
}

export function setSelectedSnapshot(id: number): void {
  state.selectedSnapshot = id;
}

export function deselectSnapshot(): void {
  state.selectedSnapshot = null;
}

export function setSnapshotCount(count: number): void {
  state.snapshotCount = count;
}

export function setChainData(data: ChainData): void {
  state.chainData = data;
}

export function setActiveNodeId(id: string | null): void {
  state.activeNodeId = id;
}

export function getSyncButtonEnabled(): boolean {
  return state.snapshotCount === 0 || state.selectedSnapshot !== null;
}

export function getOrganizarLabel(): string {
  return state.selectedSnapshot !== null
    ? `Organizar · #${state.selectedSnapshot}`
    : "Organizar";
}

export function getChainData(): ChainData | null {
  return state.chainData;
}

export function getActiveNodeId(): string | null {
  return state.activeNodeId;
}
