<script lang="ts">
  import type {
    SnapshotGroup,
    SnapshotVersion,
    Branch,
    SyncEdge,
    EditEdge,
  } from "../types";
  import GameNode from "./GameNode.svelte";
  import SnapshotGroupNode from "./SnapshotGroupNode.svelte";
  import { groupSnapshots } from "../groupSnapshots";
  import {
    getSelectedSnapshot,
    getActiveNodeId,
    deselectSnapshot
  } from "../stores.svelte";

  interface Props {
    group: SnapshotGroup;
    onselect: (id: number) => void;
    ondelete: (id: number) => void;
    onopenGame: (id: number) => void;
    onopenSync: (id: number) => void;
  }

  let { group, onselect, ondelete, onopenGame, onopenSync }: Props = $props();

  let currentIndex = $state(0);

  // Initialize and keep currentIndex synced when group changes
  $effect(() => {
    currentIndex = group.versions.length - 1;
  });

  let currentVersion = $derived(group.versions[currentIndex]!);

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

  function edgeBadgeLabel(version: SnapshotVersion): string {
    if (!version.incomingEdge) return "📥 Base";
    if (version.incomingEdge.type === "sync") return "☁️ Sync Notion";
    if (version.incomingEdge.type === "edit") return "✏️ Editado";
    return "";
  }

  function handlePrev(e: MouseEvent): void {
    e.stopPropagation();
    if (currentIndex > 0) {
      currentIndex -= 1;
      onselect(group.versions[currentIndex]!.snapshot.id);
    }
  }

  function handleNext(e: MouseEvent): void {
    e.stopPropagation();
    if (currentIndex < group.versions.length - 1) {
      currentIndex += 1;
      onselect(group.versions[currentIndex]!.snapshot.id);
    }
  }

  function handleDelete(e: MouseEvent): void {
    e.stopPropagation();
    ondelete(currentVersion.snapshot.id);
  }

  function handleClick(): void {
    onselect(currentVersion.snapshot.id);
  }

  // Group branches for recursive rendering
  // For sync/edit edges, pass the edge as initialIncomingEdge to the child group
  let groupedBranches = $derived(
    group.branches
      .filter((b) => b.output !== null)
      .map((b) => ({
        edge: b.edge,
        group:
          b.edge.type === "game"
            ? groupSnapshots([b.output!])[0]
            : groupSnapshots([b.output!], b.edge as SyncEdge | EditEdge)[0],
      }))
  );
</script>

<div class="chain-row">
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="node node-group"
    class:active={getActiveNodeId() === String(currentVersion.snapshot.id)}
    class:csv-selected={getSelectedSnapshot() === currentVersion.snapshot.id}
    data-id={currentVersion.snapshot.id}
    data-type="snapshot-group"
    onclick={handleClick}
  >
    <button
      class="node-delete-btn"
      data-snapshot-id={currentVersion.snapshot.id}
      title="Eliminar snapshot"
      onclick={handleDelete}>🗑</button
    >

    <!-- Pagination Header -->
    {#if group.versions.length > 1}
      <div class="pagination-header">
        <button
          class="pagination-btn"
          onclick={handlePrev}
          disabled={currentIndex === 0}
          title="Versión anterior"
        >
          ‹
        </button>
        <span class="pagination-label">
          v{currentIndex + 1} de {group.versions.length}
        </span>
        <button
          class="pagination-btn"
          onclick={handleNext}
          disabled={currentIndex === group.versions.length - 1}
          title="Versión siguiente"
        >
          ›
        </button>
      </div>
    {/if}

    <!-- Event Badge -->
    <div class="edge-badge">
      {edgeBadgeLabel(currentVersion)}
    </div>

    <!-- Snapshot Content -->
    <div class="node-icon">📋</div>
    <div class="node-label">Versión #{currentVersion.snapshot.id}</div>
    <div class="node-name">{esc(currentVersion.snapshot.created_at)}</div>
    <div class="node-meta">
      {currentVersion.snapshot.player_count} jugadores · {sourceLabel(
        currentVersion.snapshot.source
      )}
    </div>
    
    <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-top: 6px;">
      {#if currentVersion.snapshot.is_latest}
        <span class="badge badge-latest" style="margin-top: 0;">Actual</span>
      {/if}
      {#if getSelectedSnapshot() === currentVersion.snapshot.id}
        <button 
          class="badge badge-selected" 
          style="margin-top: 0; cursor: pointer; padding: 2px 6px;"
          title="Snapshot seleccionado. Clic para quitar selección"
          onclick={(e) => { e.stopPropagation(); deselectSnapshot(); }}
        >
          📌
        </button>
      {/if}
    </div>
  </div>

  <!-- Branches -->
  {#if groupedBranches.length > 0}
    <div class="chain-fork">
      {#each groupedBranches as branch (branch.edge.id)}
        <div class="chain-branch">
          <span class="arrow">→</span>
          {#if branch.edge.type === "game"}
            <GameNode node={branch.edge} onopen={onopenGame} />
            {#if branch.group}
              <span class="arrow">→</span>
              <SnapshotGroupNode
                group={branch.group}
                {onselect}
                {ondelete}
                {onopenGame}
                {onopenSync}
              />
            {/if}
          {:else if branch.group}
            <!-- sync/edit edges are absorbed as incomingEdge of child group -->
            <SnapshotGroupNode
              group={branch.group}
              {onselect}
              {ondelete}
              {onopenGame}
              {onopenSync}
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
    width: 180px;
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

  .node-group {
    background: var(--csv-bg);
    border-color: var(--csv-border);
  }

  :global(.node-group.latest-pending) {
    background: var(--pending-bg);
    border-color: var(--pending-border);
  }

  :global(.node.active.node-group) {
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

  .pagination-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
  }

  .pagination-btn {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 4px;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    font-size: 14px;
    font-weight: 600;
    color: var(--text);
    transition: background 0.15s, opacity 0.15s;
  }

  .pagination-btn:hover:not(:disabled) {
    background: var(--border);
  }

  .pagination-btn:disabled {
    opacity: 0.3;
    cursor: not-allowed;
  }

  .pagination-label {
    font-size: 10px;
    font-weight: 600;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }

  .edge-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 99px;
    font-size: 9px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    margin-bottom: 6px;
    background: var(--surface2);
    color: var(--muted);
    border: 1px solid var(--border);
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

  .badge-selected {
    background: #dcfce7;
    color: #166534;
    border: 1px solid #86efac;
    transition: background 0.15s;
  }
  .badge-selected:hover {
    background: #bbf7d0;
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

  :global(.node-group.csv-selected) {
    box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.4), var(--shadow-md);
  }

  :global(.node-group.csv-selected) .node-label {
    color: var(--success);
  }
</style>