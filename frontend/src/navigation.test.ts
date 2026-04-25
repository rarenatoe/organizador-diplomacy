import { nav, type PanelContext } from "./navigation.svelte";
import * as stores from "./stores.svelte";

// Spy on the active node setter
vi.mock("./stores.svelte", () => ({
  setActiveNodeId: vi.fn(),
}));

describe("NavigationManager", () => {
  beforeEach(() => {
    nav.close(); // Reset singleton state before each test
    vi.clearAllMocks();
  });

  const mockSnapshotPanel: PanelContext = {
    title: "Snap 1",
    type: "snapshot",
    id: 1,
  };
  const mockGamePanel: PanelContext = { title: "Game 2", type: "game", id: 2 };

  it("should initialize empty", () => {
    expect(nav.isOpen).toBe(false);
    expect(nav.current).toBeNull();
  });

  it("push() should add to the stack and set active node", () => {
    nav.push(mockSnapshotPanel);

    expect(nav.isOpen).toBe(true);
    expect(nav.current).toEqual(mockSnapshotPanel);
    expect(stores.setActiveNodeId).toHaveBeenCalledWith(1);
  });

  it("pop() should return to the previous panel and restore active node", () => {
    nav.push(mockSnapshotPanel);
    nav.push(mockGamePanel);

    expect(nav.current).toEqual(mockGamePanel);

    nav.pop();

    expect(nav.current).toEqual(mockSnapshotPanel);
    expect(stores.setActiveNodeId).toHaveBeenCalledWith(1);
  });

  it("pop() on the last item should close the panel and clear active node", () => {
    nav.push(mockSnapshotPanel);
    nav.pop();

    expect(nav.isOpen).toBe(false);
    expect(nav.current).toBeNull();
    expect(stores.setActiveNodeId).toHaveBeenCalledWith(null);
  });

  it("clearAndPush() should wipe the stack and start fresh", () => {
    nav.push(mockSnapshotPanel);
    nav.clearAndPush(mockGamePanel);

    expect(nav.stack.length).toBe(1);
    expect(nav.current).toEqual(mockGamePanel);
    expect(stores.setActiveNodeId).toHaveBeenCalledWith(2);
  });
});
