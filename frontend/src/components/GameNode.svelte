<script lang="ts">
  import type { GameEdge } from "../types";

  interface Props {
    node: GameEdge;
    onopen: (id: number) => void;
  }

  let { node, onopen }: Props = $props();

  let date = $derived((node.created_at || "").split(" ")[0] ?? "");
  let time = $derived((node.created_at || "").split(" ")[1] ?? "");
</script>

<div class="node node-report" data-id={node.id} data-type="game" role="button" tabindex="0" onclick={() => onopen(node.id)} onkeydown={(e) => e.key === "Enter" && onopen(node.id)}>
  <div class="node-icon">📊</div>
  <div class="node-label">Jornada</div>
  <div class="node-name">{date}</div>
  <div class="node-meta">{time}<br />{node.mesa_count} partida(s)<br />{node.espera_count} en espera</div>
</div>

<style>
  .node {
    cursor: pointer;
    border-radius: var(--radius);
    padding: 14px 16px;
    width: 156px;
    flex-shrink: 0;
    box-shadow: var(--shadow);
    transition: transform 0.15s, box-shadow 0.15s, border-color 0.15s;
    border: 2px solid transparent;
    user-select: none;
    position: relative;
  }

  .node:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
  }

  :global(.node.active) {
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.25);
  }

  .node-report {
    background: var(--report-bg);
    border-color: var(--report-border);
  }

  :global(.node.active.node-report) {
    border-color: var(--report-border);
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
    color: var(--muted);
    margin-bottom: 3px;
  }

  .node-name {
    font-size: 12px;
    font-weight: 600;
    color: var(--text);
    word-break: break-all;
    line-height: 1.4;
  }

  .node-meta {
    font-size: 11px;
    color: var(--muted);
    margin-top: 6px;
    line-height: 1.6;
  }
</style>
