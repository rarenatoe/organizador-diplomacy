<script lang="ts">
  import type { Snippet } from "svelte";
  import type { GameDraftPlayer } from "../../generated-api";
  import PlayerName from "../ui/PlayerName.svelte";
  import { cx } from "../../utils/css";

  interface Props {
    player: GameDraftPlayer;
    cuposText: string;
    isActive?: boolean;
    actions?: Snippet;
  }

  let { player, cuposText, isActive = false, actions }: Props = $props();
</script>

<div
  class={cx(
    "waiting-item",
    isActive && "swapping-active",
    actions && "has-actions",
  )}
>
  <PlayerName {player} compact={true} showNotionIndicator={false} />
  <span class="waiting-cupos">{cuposText}</span>
  {#if actions}
    {@render actions()}
  {/if}
</div>

<style>
  .waiting-item {
    display: grid;
    /* Base layout (no actions) */
    grid-template-columns: 1fr var(--space-56);
    align-items: center;
    padding: var(--space-4) var(--space-8);
    background: var(--warning-bg-subtle);
    border: 1px solid var(--warning-border-subtle);
    border-radius: var(--space-8);
    font-size: 12px;
  }

  .waiting-item.has-actions {
    /* Extended layout when the button snippet is provided */
    grid-template-columns: 1fr var(--space-56) var(--space-32);
  }

  .swapping-active {
    background: var(--info-bg-subtle);
    outline: var(--space-4) solid var(--border-focus);
    border-color: var(--border-focus);
  }

  .waiting-cupos {
    color: var(--warning-text-subtle);
    font-size: 11px;
    text-align: right;
  }
</style>
