<script lang="ts">
  import type { Snippet } from "svelte";
  import type { GameDraftPlayer } from "../../generated-api";
  import PlayerName from "../ui/PlayerName.svelte";
  import { cx } from "../../utils/css";

  interface Props {
    players: GameDraftPlayer[];
    isSwapping?: (index: number) => boolean;
    actions?: Snippet<[number]>; // Passes the index back to the parent
  }

  let { players, isSwapping = () => false, actions }: Props = $props();
</script>

<div class="waitlist-container">
  {#each players as player, i (player.nombre + "_" + i)}
    <div
      class={cx(
        "waiting-item",
        isSwapping(i) && "swapping-active",
        actions && "has-actions",
      )}
    >
      <PlayerName {player} compact={true} showNotionIndicator={false} />

      <span class="waiting-cupos">
        {player.cupos_faltantes ?? player.partidas_deseadas} cupo(s)
      </span>

      {#if actions}
        {@render actions(i)}
      {/if}
    </div>
  {/each}
</div>

<style>
  .waitlist-container {
    display: flex;
    flex-direction: column;
    gap: var(--space-4); /* Standardized gap */
  }

  .waiting-item {
    display: grid;
    grid-template-columns: 1fr var(--space-72);
    align-items: center;
    padding: var(--space-4) var(--space-8);
    background: var(--warning-bg-subtle);
    border: 1px solid var(--warning-border-subtle);
    border-radius: var(--space-8);
    font-size: 12px;
    min-height: var(--space-32); /* Fixes the height discrepancy */
  }

  .waiting-item.has-actions {
    grid-template-columns: 1fr var(--space-72) var(--space-32);
  }

  .swapping-active {
    background: var(--info-bg-subtle);
    outline: 2px solid var(--border-focus);
    border-color: var(--border-focus);
  }

  .waiting-cupos {
    color: var(--warning-text-subtle);
    font-size: 11px;
    text-align: right;
  }
</style>
