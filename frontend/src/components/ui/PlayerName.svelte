<script
  lang="ts"
  generics="T extends { nombre: string; notion_id?: string | null; notion_name?: string | null }"
>
  import type { PlayerAutocompleteItem } from "../../generated-api";
  import { normalizeName } from "../../utils";
  import PlayerAutocompleteInput from "../features/PlayerAutocompleteInput.svelte";
  import Tooltip from "./Tooltip.svelte";

  interface Props {
    player: T;
    editable?: boolean;
    showNotionIndicator?: boolean;
    compact?: boolean;
    knownPlayers?: PlayerAutocompleteItem[];
    existingPlayers?: T[];
  }

  let {
    player = $bindable() as T,
    editable = false,
    showNotionIndicator = true,
    compact = false,
    knownPlayers = [],
    existingPlayers = [],
  }: Props = $props();

  let isNotionLinked = $derived(!!player.notion_id || !!player.notion_name);
  let showAlias = $derived(
    player.notion_name &&
      normalizeName(player.notion_name) !== normalizeName(player.nombre),
  );
</script>

<div class="player-name-wrapper" class:compact>
  {#if editable}
    <PlayerAutocompleteInput
      bind:value={player.nombre}
      {knownPlayers}
      {existingPlayers}
      currentPlayer={player}
      wrapperClass="name-element autocomplete-wrapper"
      class="table-input table-input-ghost text-strong"
      placeholder="Nombre del jugador"
      onConfirm={(input) => {
        if (typeof input === "string") {
          player.nombre = input;
        } else {
          player.nombre = input.nombre;
          if (input.notion_id) player.notion_id = input.notion_id;
          if (input.notion_name) player.notion_name = input.notion_name;
        }
      }}
    />
  {:else}
    <span
      class="text-strong name-element read-only-name"
      class:compact-text={compact}
    >
      {player.nombre}
    </span>
  {/if}

  {#if showAlias && !compact}
    <span class="notion-alias-hint" title="Nombre en Notion"
      >({player.notion_name})</span
    >
  {/if}

  {#if showNotionIndicator && isNotionLinked}
    <Tooltip
      text="Vinculado a Notion. Los cambios futuros se sincronizarán automáticamente."
      icon="⚡️"
    />
  {/if}
</div>

<style>
  .player-name-wrapper {
    display: flex;
    align-items: center;
    gap: var(--space-4);
    min-width: 0;
    width: 100%; /* Force wrapper to fill the table cell */
  }

  .name-element {
    flex: 1;
    min-width: 0; /* Allow both input wrapper and read-only span to shrink */
  }

  /* Target ONLY the autocomplete wrapper, keeping it out of the read-only span's way */
  :global(.autocomplete-wrapper) {
    display: block;
    width: 100%;
  }

  /* Ensure the inner input shrinks correctly and takes full width */
  :global(.autocomplete-wrapper input) {
    width: 100%;
    min-width: 0; /* Critical: allows input to shrink below browser's intrinsic default */
    box-sizing: border-box;
  }

  .read-only-name {
    /* Mimic the padding of .table-input to prevent layout shift */
    padding: var(--space-4) var(--space-8);
  }

  .player-name-wrapper.compact .read-only-name {
    padding: 0;
  }
  .player-name-wrapper.compact {
    gap: var(--space-2);
  }
  .compact-text {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .notion-alias-hint {
    font-size: 11px;
    color: var(--text-muted);
  }
</style>
