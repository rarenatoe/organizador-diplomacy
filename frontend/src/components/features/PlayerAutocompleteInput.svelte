<script
  lang="ts"
  generics="T extends { nombre: string; notion_id?: string | null; notion_name?: string | null }"
>
  import type { AutocompletePlayer, SimilarName, MergePair } from "../../types";
  import { createAutocompleteState } from "./playerAutocompleteState.svelte.ts";
  import { clickOutside } from "../../clickOutside";
  import { checkPlayerSimilarity } from "../../api";
  import { normalizeName } from "../../utils";
  import SyncResolutionModal from "../modals/SyncResolutionModal.svelte";
  import { cx } from "../../utils/css.ts";

  interface Props {
    value: string;
    onConfirm: (
      input: string | AutocompletePlayer,
      silentDuplicate?: boolean,
    ) => void;
    placeholder?: string;
    knownPlayers?: AutocompletePlayer[];
    existingPlayers?: T[];
    currentPlayer?: T;
    onClickOutside?: () => void;
    class?: string;
    wrapperClass?: string;
    clearOnConfirm?: boolean;
    autofocus?: boolean;
  }

  let {
    value = $bindable(),
    onConfirm,
    placeholder = "Escribe para buscar o agregar...",
    knownPlayers = [],
    existingPlayers = [],
    currentPlayer,
    onClickOutside,
    class: className = "input-field text-strong",
    wrapperClass = "",
    clearOnConfirm = false,
    autofocus = false,
  }: Props = $props();

  let isActive = $state(false);

  // Create state instance with reactive props
  let autocompleteState = createAutocompleteState<T>([], []);

  $effect(() => {
    autocompleteState.updateKnownPlayers(knownPlayers);
    autocompleteState.updateExistingPlayers(existingPlayers);
    autocompleteState.syncExternalValue(value);
  });

  type ResolutionState =
    | { status: "idle" }
    | { status: "resolving"; input: string; pairs: SimilarName[] };

  let resolutionState = $state<ResolutionState>({ status: "idle" });

  // Check if dropdown is open
  let isDropdownOpen = $derived(
    isActive &&
      autocompleteState.searchQuery.trim().length > 0 &&
      autocompleteState.suggestions.length > 0,
  );

  function executeConfirm(
    input: string | AutocompletePlayer,
    silentDuplicate: boolean = false,
  ) {
    isActive = false; // Add this line
    onConfirm(input, silentDuplicate);
    if (clearOnConfirm) value = "";
    autocompleteState.reset();
  }

  // Keep external value in sync with state
  $effect(() => {
    autocompleteState.syncExternalValue(value);
  });

  async function handleSimilarityCheck(input: string) {
    // Pre-flight check: if player already exists in existingPlayers, bypass API and modal
    if (
      existingPlayers.some(
        (p) =>
          p !== currentPlayer &&
          normalizeName(p.nombre) === normalizeName(input),
      )
    ) {
      executeConfirm(input);
      return;
    }

    try {
      const result = await checkPlayerSimilarity([input]);

      if (result.similarities && result.similarities.length > 0) {
        // Set the unified resolving state (this replaces all three old variables)
        resolutionState = {
          status: "resolving",
          input,
          pairs: enrichSimilaritiesWithDraft(result.similarities),
        };
      } else {
        // No similarities found, proceed with original input
        executeConfirm(input);
      }
    } catch (error) {
      // Error in similarity check, proceed with original input
      executeConfirm(input);
    }
  }

  function handleResolutionComplete(merges: MergePair[]) {
    if (resolutionState.status !== "resolving") return;
    const { input: originalName } = resolutionState;
    resolutionState = { status: "idle" };

    const mergeTarget = merges.find((m) => m.from === originalName);

    if (!mergeTarget || mergeTarget.action === "skip") {
      return executeConfirm(originalName);
    }

    if (mergeTarget.action === "use_existing") {
      return executeConfirm(
        {
          display: mergeTarget.to,
          nombre: mergeTarget.to,
          notion_id: mergeTarget.notion_id,
          is_local: true,
          is_alias: false,
        } as AutocompletePlayer,
        true,
      );
    }

    const shouldRename = ["link_rename", "merge_notion"].includes(
      mergeTarget.action,
    );
    const finalName = shouldRename ? mergeTarget.to : originalName;
    executeConfirm({
      display: finalName,
      nombre: finalName,
      notion_id: mergeTarget.notion_id,
      notion_name: mergeTarget.to,
      is_local: true,
      is_alias: false,
    } as AutocompletePlayer);
  }

  function handleResolutionCancel() {
    resolutionState = { status: "idle" };
    if (clearOnConfirm) value = "";
    autocompleteState.reset();
  }

  function handleFocusOnMount(node: HTMLInputElement) {
    if (autofocus) {
      node.focus();
    }
  }

  function handleClickOutside() {
    isActive = false; // Add this line
    if (onClickOutside) {
      onClickOutside();
    }
  }

  function enrichSimilaritiesWithDraft(
    similarities: SimilarName[],
  ): SimilarName[] {
    return similarities.map((sim) => {
      if (sim.notion_id) {
        const draftMatch = existingPlayers.find(
          (p) => p.notion_id === sim.notion_id,
        );
        if (draftMatch) {
          return { ...sim, existing_local_name: draftMatch.nombre };
        }
      }
      return sim;
    });
  }
</script>

<div
  use:clickOutside={{ callback: handleClickOutside }}
  class={cx(wrapperClass, isDropdownOpen && "active-dropdown")}
  style="position: relative;"
>
  <input
    type="text"
    class={className}
    bind:value
    {placeholder}
    use:handleFocusOnMount
    onfocus={() => (isActive = true)}
    oninput={() => (isActive = true)}
    onkeydown={(e) => {
      const currentVal = (e.target as HTMLInputElement).value.trim();
      if (e.key === "Enter") {
        e.preventDefault();
        const selectedSuggestion =
          autocompleteState.suggestions[autocompleteState.selectedIndex];
        if (autocompleteState.selectedIndex >= 0 && selectedSuggestion) {
          autocompleteState.selectPlayer(selectedSuggestion, (input) =>
            executeConfirm(input),
          );
        } else if (currentVal) {
          value = currentVal; // Force bind update
          handleSimilarityCheck(currentVal);
        }
      } else {
        autocompleteState.handleKeydown(e, (input) => executeConfirm(input));
      }
    }}
  />
  {#if isDropdownOpen}
    <div class="autocomplete-dropdown">
      {#each autocompleteState.suggestions as suggestion, index (suggestion.display)}
        <button
          type="button"
          class="autocomplete-item"
          class:active={autocompleteState.selectedIndex === index}
          onclick={() =>
            autocompleteState.selectPlayer(suggestion, executeConfirm)}
        >
          {suggestion.display}
          {#if suggestion.is_alias && suggestion.notion_name}
            <span class="alias-text text-gray-400">
              ↪ {suggestion.notion_name}</span
            >
          {/if}
        </button>
      {/each}
    </div>
  {/if}
</div>

{#if resolutionState.status === "resolving"}
  <SyncResolutionModal
    visible={true}
    pairs={resolutionState.pairs}
    onComplete={handleResolutionComplete}
    onCancel={handleResolutionCancel}
  />
{/if}

<style>
  /* Autocomplete Dropdown Styling */
  .autocomplete-dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    margin-top: var(--space-4);
    background: var(--bg-secondary);
    border: 1px solid var(--border-default);
    border-radius: var(--space-8);
    z-index: 9999;
    max-height: calc(var(--space-8) * 25);
    overflow-y: auto;
    width: 100%;
    box-shadow: var(--shadow-lg);
  }

  .autocomplete-item {
    padding: var(--space-8) var(--space-16);
    cursor: pointer;
    border: none;
    border-bottom: 1px solid var(--border-subtle);
    background: transparent;
    width: 100%;
    text-align: left;
    color: var(--text-primary);
    font-size: 13px;
    font-family: inherit;
    transition: background-color var(--transition-fast);
  }

  .autocomplete-item:last-child {
    border-bottom: none;
  }

  .autocomplete-item:hover,
  .autocomplete-item:focus {
    background: var(--bg-tertiary);
    outline: none;
  }

  .autocomplete-item.active {
    background: var(--bg-tertiary);
    outline: 2px solid var(--accent-primary);
    outline-offset: -2px;
  }

  .alias-text {
    color: var(--text-muted);
    font-size: 11px;
    margin-left: var(--space-8);
    font-style: italic;
  }

  :global(.active-dropdown) {
    z-index: 50; /* Ensure it floats above subsequent table rows and sticky columns */
  }
</style>
