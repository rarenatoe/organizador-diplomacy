<script
  lang="ts"
  generics="T extends { nombre: string; notion_id?: string | null; notion_name?: string | null }"
>
  import { normalizeName } from "../../utils";
  import Tooltip from "./Tooltip.svelte";

  interface Props {
    player: T;
    editable?: boolean;
    showNotionIndicator?: boolean;
    compact?: boolean;
  }

  let {
    player = $bindable() as T,
    editable = false,
    showNotionIndicator = true,
    compact = false,
  }: Props = $props();

  let isNotionLinked = $derived(!!player.notion_id || !!player.notion_name);
  let showAlias = $derived(
    player.notion_name &&
      normalizeName(player.notion_name) !== normalizeName(player.nombre),
  );
</script>

<div class="player-name-wrapper" class:compact>
  {#if editable}
    <input
      type="text"
      class="table-input table-input-ghost text-strong name-element"
      bind:value={player.nombre}
      placeholder="Nombre del jugador"
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
    min-width: 0; /* Allow both input and span to shrink without blowing out grid */
  }

  .read-only-name {
    /* Mimic the padding of .table-input to prevent layout shift between Draft and Detail views */
    padding: var(--space-4) var(--space-8);
  }

  .player-name-wrapper.compact .read-only-name {
    /* Remove padding in dense UI areas like Game Cards */
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
