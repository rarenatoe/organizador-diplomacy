<script lang="ts">
  import type { GameEdge } from "../../types";
  import { getActiveNodeId } from "../../stores.svelte";
  import Button from "../ui/Button.svelte";

  interface Props {
    node: GameEdge;
    onOpen: (id: number) => void;
    onDelete?: (id: number) => void;
  }

  let { node, onOpen, onDelete }: Props = $props();

  let date = $derived((node.created_at || "").split(" ")[0] ?? "");
  let time = $derived((node.created_at || "").split(" ")[1] ?? "");
</script>

<div
  class="node node-report group"
  class:active={getActiveNodeId() === node.id}
  data-id={node.id}
  data-type="game"
  role="button"
  tabindex="0"
  onclick={() => onOpen(node.id)}
  onkeydown={(e) => e.key === "Enter" && onOpen(node.id)}
>
  {#if onDelete}
    <Button
      variant="ghost"
      destructive={true}
      size="xs"
      iconOnly={true}
      icon="🗑"
      class="absolute-top-right group-hover-reveal"
      title="Eliminar jornada"
      onclick={(e) => {
        e.stopPropagation();
        onDelete(node.id);
      }}
    />
  {/if}

  <div class="node-icon">📊</div>
  <div class="node-label">Jornada</div>
  <div class="node-name">{date}</div>
  <div class="node-meta">
    {time}<br />{node.mesa_count} partida(s)<br />{node.espera_count} en espera
  </div>
</div>

<style>
  .node {
    cursor: pointer;
    border-radius: var(--border-radius);
    padding: 14px 16px;
    width: 156px;
    min-height: 160px;
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
    box-shadow: var(--shadow-base);
    transition:
      transform 0.15s,
      box-shadow 0.15s,
      border-color 0.15s;
    border: 2px solid transparent;
    user-select: none;
    position: relative;
  }

  .node:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
  }

  :global(.node.active) {
    box-shadow: 0 0 0 3px var(--active-glow);
    z-index: 45;
  }

  .node-report {
    background: var(--bg-secondary);
    border: 1px solid var(--border-subtle);
    border-left: 4px solid var(--green-400);
  }

  :global(.node.active.node-report) {
    background: var(--green-50);
    border-color: var(--green-500);
    border-left: 4px solid var(--green-600);
  }

  .node-icon {
    font-size: 20px;
    margin-bottom: 5px;
  }

  .node-label {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-muted);
    margin-bottom: 3px;
  }

  .node-name {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-primary);
    word-break: break-all;
    line-height: 1.4;
  }

  .node-meta {
    font-size: 11px;
    color: var(--text-muted);
    margin-top: 6px;
    line-height: 1.6;
  }
</style>
