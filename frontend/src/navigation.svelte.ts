import { setActiveNodeId } from "./stores.svelte";
import type { EditPlayerRow, DraftResponse } from "./types";

export interface PanelContext {
  title: string;
  type: "snapshot" | "game" | "sync" | "draft" | "game_draft";
  id: number | null;
  draftProps?: {
    parentId: number | null;
    eventType: "sync" | "manual" | "edit";
    autoAction: "notion" | "csv" | null;
    initialPlayers: EditPlayerRow[];
    initialData: DraftResponse | null;
    editingGameId: number | null;
    draftKey: number;
  };
}

class NavigationManager {
  stack = $state<PanelContext[]>([]);

  get current(): PanelContext | null {
    return this.stack[this.stack.length - 1] || null;
  }

  get isOpen(): boolean {
    return this.stack.length > 0;
  }

  push(panel: PanelContext): void {
    this.stack.push(panel);
    if (panel.id !== null) setActiveNodeId(panel.id);
  }

  pop = (): void => {
    this.stack.pop();
    if (this.current && this.current.id !== null) {
      setActiveNodeId(this.current.id);
    } else {
      setActiveNodeId(null);
    }
  };

  clearAndPush(panel: PanelContext): void {
    this.stack = [panel];
    if (panel.id !== null) setActiveNodeId(panel.id);
  }

  close = (): void => {
    this.stack = [];
    setActiveNodeId(null);
  };
}

export const nav = new NavigationManager();
