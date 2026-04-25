import { setActiveNodeId } from "./stores.svelte";
import type { EditPlayerRow } from "./types";
import type {
  SnapshotSaveEventType,
  GameDraftResponseOutput,
} from "./generated-api";

export interface PanelContext {
  title: string;
  type: "snapshot" | "game" | "sync" | "draft" | "game_draft";
  id: number | null;
  draftProps?: {
    parentId: number | null;
    saveEventType: SnapshotSaveEventType;
    autoAction: "notion" | "csv" | null;
    initialPlayers: EditPlayerRow[];
    initialData: GameDraftResponseOutput | null;
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
