<script lang="ts">
  import type { SnapshotNode } from "../types";
  import GameNode from "./GameNode.svelte";
  import SyncNode from "./SyncNode.svelte";
  import EditNode from "./EditNode.svelte";
  import SnapshotNodeComponent from "./SnapshotNode.svelte";

  interface Props {
    node: SnapshotNode;
    onselect: (id: number) => void;
    ondelete: (id: number) => void;
  }

  let { node, onselect, ondelete }: Props = $props();

  let branches = $derived(node.branches ?? []);

  function esc(s: string | null | undefined): string {
    const el = document.createElement("span");
    el.textContent = s ?? "";
    return el.innerHTML;
  }

  function sourceLabel(source: string): string {
    if (source === "notion_sync") return "☁️ Notion Sync";
    if (source === "organizar") return "▶ Organizar";
    return "📥 Manual";
  }

  function handleDelete(e: MouseEvent): void {
    e.stopPropagation();
    ondelete(node.id);
  }

  function handleClick(): void {
    onselect(node.id);
  }
</script>

<div class="chain-row">
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="node node-csv"
    data-id={node.id}
    data-type="snapshot"
    onclick={handleClick}
  >
    <button
      class="node-delete-btn"
      data-snapshot-id={node.id}
      title="Eliminar snapshot"
      onclick={handleDelete}>🗑</button
    >
    <div class="node-icon">📋</div>
    <div class="node-label">Snapshot #{node.id}</div>
    <div class="node-name">{esc(node.created_at)}</div>
    <div class="node-meta">
      {node.player_count} jugadores · {sourceLabel(node.source)}
    </div>
    {#if node.is_latest}
      <span class="badge badge-latest">Actual</span>
    {/if}
  </div>
  {#if branches.length > 0}
    <div class="chain-fork">
      {#each branches as branch (branch.edge.id)}
        <div class="chain-branch">
          <span class="arrow">→</span>
          {#if branch.edge.type === "sync"}
            <SyncNode node={branch.edge} />
          {:else if branch.edge.type === "edit"}
            <EditNode node={branch.edge} />
          {:else}
            <GameNode node={branch.edge} />
          {/if}
          {#if branch.output}
            <span class="arrow">→</span>
            <SnapshotNodeComponent
              node={branch.output}
              {onselect}
              {ondelete}
            />
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .chain-row {
    display: flex;
    align-items: center;
  }

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

  .node-csv {
    background: var(--csv-bg);
    border-color: var(--csv-border);
  }

  :global(.node-csv.latest-pending) {
    background: var(--pending-bg);
    border-color: var(--pending-border);
  }

  :global(.node.active.node-csv) {
    border-color: var(--csv-border);
  }

  .node-delete-btn {
    position: absolute;
    top: 5px;
    right: 5px;
    background: transparent;
    border: none;
    cursor: pointer;
    font-size: 11px;
    opacity: 0;
    transition: opacity 0.15s, background 0.15s;
    padding: 2px 4px;
    border-radius: 4px;
    line-height: 1;
  }

  .node:hover .node-delete-btn,
  :global(.node.active) .node-delete-btn {
    opacity: 1;
  }

  .node-delete-btn:hover {
    background: rgba(239, 68, 68, 0.15);
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

  .badge {
    display: inline-block;
    padding: 2px 7px;
    border-radius: 99px;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    margin-top: 5px;
  }

  :global(.badge-pending) {
    background: #fef3c7;
    color: #92400e;
    border: 1px solid var(--pending-border);
  }

  .badge-latest {
    background: #dbeafe;
    color: #1e40af;
    border: 1px solid #93c5fd;
  }

  .arrow {
    color: #9ca3af;
    font-size: 18px;
    padding: 0 6px;
    flex-shrink: 0;
    user-select: none;
  }

  .chain-fork {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .chain-branch {
    display: flex;
    align-items: center;
  }

  :global(.node-csv.csv-selected) {
    box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.4), var(--shadow-md);
  }

  :global(.node-csv.csv-selected) .node-label {
    color: var(--success);
  }
</style>