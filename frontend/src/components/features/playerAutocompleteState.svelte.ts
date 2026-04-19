import type { PlayerAutocompleteItem } from "../../generated-api";

export function createAutocompleteState<
  T extends { nombre: string; notion_id?: string | null },
>(initialKnown: PlayerAutocompleteItem[] = [], initialExisting: T[] = []) {
  let searchQuery = $state("");
  let selectedIndex = $state(-1);
  let knownPlayers = $state(initialKnown);
  let existingPlayers = $state<T[]>(initialExisting);

  const suggestions = $derived.by(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return [];

    return knownPlayers
      .filter((player) => {
        if (!player.display.toLowerCase().includes(query)) return false;
        return !existingPlayers.some(
          (p) =>
            p.nombre === player.nombre ||
            (player.notion_id && p.notion_id === player.notion_id),
        );
      })
      .slice(0, 10);
  });

  function reset() {
    searchQuery = "";
    selectedIndex = -1;
  }

  return {
    get searchQuery() {
      return searchQuery;
    },
    get selectedIndex() {
      return selectedIndex;
    },
    get suggestions() {
      return suggestions;
    },

    updateKnownPlayers(players: PlayerAutocompleteItem[]) {
      knownPlayers = players;
    },
    updateExistingPlayers(players: T[]) {
      existingPlayers = players;
    },
    syncExternalValue(val: string) {
      searchQuery = val;
    },
    reset,
    handleKeydown(
      e: KeyboardEvent,
      onConfirm: (input: string | PlayerAutocompleteItem) => void,
    ) {
      if (e.key === "Enter") {
        e.preventDefault();
        if (selectedIndex >= 0 && selectedIndex < suggestions.length) {
          const selectedPlayer = suggestions[selectedIndex];
          onConfirm(selectedPlayer || searchQuery);
        } else if (searchQuery.trim()) {
          onConfirm(searchQuery.trim());
        }
        reset();
      } else if (e.key === "Escape") {
        reset();
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        if (suggestions.length > 0) {
          selectedIndex = (selectedIndex + 1) % suggestions.length;
        }
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        if (suggestions.length > 0) {
          selectedIndex =
            selectedIndex <= 0 ? suggestions.length - 1 : selectedIndex - 1;
        }
      }
    },
    selectPlayer(
      player: PlayerAutocompleteItem,
      onConfirm: (input: string | PlayerAutocompleteItem) => void,
    ) {
      onConfirm(player);
      reset();
    },
  };
}
