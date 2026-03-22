import { describe, it, expect, beforeEach } from "vitest";
import "@testing-library/jest-dom";
import {
  getSelectedSnapshot,
  setSelectedSnapshot,
  deselectSnapshot,
  setSnapshotCount,
  updateSelectionUI,
} from "./selection";

describe("selection", () => {
  beforeEach(() => {
    // Reset DOM
    document.body.innerHTML = `
      <button id="btn-sync">Sync Notion</button>
      <button id="btn-deselect">✕</button>
      <span id="organizar-label">Organizar</span>
    `;
    // Reset selection state by deselecting
    deselectSnapshot();
    setSnapshotCount(0);
  });

  describe("getSelectedSnapshot", () => {
    it("should return null initially", () => {
      expect(getSelectedSnapshot()).toBeNull();
    });

    it("should return the selected snapshot id after selection", () => {
      setSelectedSnapshot(42);
      expect(getSelectedSnapshot()).toBe(42);
    });

    it("should return null after deselection", () => {
      setSelectedSnapshot(42);
      deselectSnapshot();
      expect(getSelectedSnapshot()).toBeNull();
    });
  });

  describe("Sync Notion button state", () => {
    it("should be enabled when no snapshots exist (initial sync)", () => {
      setSnapshotCount(0);
      updateSelectionUI();
      const btnSync = document.getElementById("btn-sync") as HTMLButtonElement;
      expect(btnSync.disabled).toBe(false);
    });

    it("should be disabled when snapshots exist but none are selected", () => {
      setSnapshotCount(3);
      updateSelectionUI();
      const btnSync = document.getElementById("btn-sync") as HTMLButtonElement;
      expect(btnSync.disabled).toBe(true);
    });

    it("should be enabled when a snapshot is selected", () => {
      setSnapshotCount(3);
      setSelectedSnapshot(1);
      const btnSync = document.getElementById("btn-sync") as HTMLButtonElement;
      expect(btnSync.disabled).toBe(false);
    });

    it("should be disabled after deselecting when snapshots exist", () => {
      setSnapshotCount(3);
      setSelectedSnapshot(1);
      deselectSnapshot();
      const btnSync = document.getElementById("btn-sync") as HTMLButtonElement;
      expect(btnSync.disabled).toBe(true);
    });

    it("should remain enabled when no snapshots exist even after deselecting", () => {
      setSnapshotCount(0);
      setSelectedSnapshot(1);
      deselectSnapshot();
      const btnSync = document.getElementById("btn-sync") as HTMLButtonElement;
      expect(btnSync.disabled).toBe(false);
    });
  });

  describe("updateSelectionUI", () => {
    it("should update organizar label when snapshot is selected", () => {
      setSelectedSnapshot(5);
      const label = document.getElementById("organizar-label");
      expect(label?.textContent).toBe("Organizar · #5");
    });

    it("should reset organizar label when snapshot is deselected", () => {
      setSelectedSnapshot(5);
      deselectSnapshot();
      const label = document.getElementById("organizar-label");
      expect(label?.textContent).toBe("Organizar");
    });

    it("should show deselect button when snapshot is selected", () => {
      setSelectedSnapshot(5);
      const deselBtn = document.getElementById("btn-deselect") as HTMLElement;
      expect(deselBtn.style.display).toBe("");
    });

    it("should hide deselect button when no snapshot is selected", () => {
      const deselBtn = document.getElementById("btn-deselect") as HTMLElement;
      expect(deselBtn.style.display).toBe("none");
    });
  });
});
