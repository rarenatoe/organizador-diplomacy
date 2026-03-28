<script lang="ts">
  import { untrack } from "svelte";
  import type {
    SnapshotGroup,
    SyncEdge,
    EditEdge,
  } from "../types";
  import GameNode from "./GameNode.svelte";
  import SnapshotGroupNode from "./SnapshotGroupNode.svelte";
  import { groupSnapshots } from "../groupSnapshots";
  import {
    getActiveNodeId
  } from "../stores.svelte";

  interface Props {
    group: SnapshotGroup;
    onSelect: (id: number) => void;
    onDelete: (id: number) => void;
    onOpenGame: (id: number) => void;
    onOpenSync: (id: number) => void;
  }

  let { group, onSelect, onDelete, onOpenGame, onOpenSync }: Props = $props();

  // `untrack` reads the initial prop value without creating a reactive
  // dependency — avoids `state_referenced_locally` while initialising to the
  // last (latest) version.  User nav (handlePrev / handleNext) can override.
  let currentIndex = $state(untrack(() => group.versions.length - 1));

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

  function handlePrev(e: MouseEvent): void {
    e.stopPropagation();
    if (currentIndex > 0) {
      currentIndex -= 1;
      onSelect(group.versions[currentIndex]!.snapshot.id);
    }
  }

  function handleNext(e: MouseEvent): void {
    e.stopPropagation();
    if (currentIndex < group.versions.length - 1) {
      currentIndex += 1;
      onSelect(group.versions[currentIndex]!.snapshot.id);
    }
  }

  function handleDelete(e: MouseEvent): void {
    e.stopPropagation();
    onDelete(currentVersion.snapshot.id);
  }

  function handleClick(): void {
    onSelect(currentVersion.snapshot.id);
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
  <div class="node-wrapper">
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
      class="node node-group"
      class:active={getActiveNodeId() === currentVersion.snapshot.id}
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

      <div class="node-icon">📋</div>
      <div class="node-label">Versión #{currentVersion.snapshot.id}</div>
      <div class="node-name">{esc(currentVersion.snapshot.created_at)}</div>
      <div class="node-meta">
        {currentVersion.snapshot.player_count} jugadores · {sourceLabel(
          currentVersion.snapshot.source
        )}
      </div>
      
      <div class="node-badges">
        {#if currentVersion.snapshot.is_latest}
          <span class="badge badge-latest">Actual</span>
        {/if}
      </div>
    </div>

    {#if group.versions.length > 1}
      <div class="pagination-pill">
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
  </div>

  <!-- Branches -->
  {#if groupedBranches.length > 0}
    <div class="chain-fork">
      {#each groupedBranches as branch (branch.edge.id)}
        <div class="chain-branch">
          <span class="arrow">→</span>
          {#if branch.edge.type === "game"}
            <GameNode node={branch.edge} onOpen={onOpenGame} />
            {#if branch.group}
              <span class="arrow">→</span>
              <SnapshotGroupNode
                group={branch.group}
                {onSelect}
                {onDelete}
                {onOpenGame}
                {onOpenSync}
              />
            {/if}
          {:else if branch.group}
            <!-- sync/edit edges are absorbed as incomingEdge of child group -->
            <SnapshotGroupNode
              group={branch.group}
              {onSelect}
              {onDelete}
              {onOpenGame}
              {onOpenSync}
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
    min-height: 160px;
    display: flex;
    flex-direction: column;
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
    z-index: 45;
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

  .node-wrapper {
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
    flex-shrink: 0;
  }

  .pagination-pill {
    position: absolute;
    bottom: -14px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2px 6px;
    gap: 6px;
    box-shadow: var(--shadow);
    z-index: 50;
  }

  .pagination-btn {
    background: transparent;
    border: none;
    border-radius: 50%;
    width: 22px;
    height: 22px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    font-size: 15px;
    font-weight: 600;
    color: var(--text);
    transition: background 0.15s, opacity 0.15s;
  }

  .pagination-btn:hover:not(:disabled) {
    background: var(--surface2);
  }

  .pagination-btn:disabled {
    opacity: 0.3;
    cursor: not-allowed;
  }

  .pagination-label {
    font-size: 10px;
    font-weight: 700;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.3px;
    user-select: none;
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

  .node-badges {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    margin-top: auto;
    min-height: 18px;
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

  :global(.node-group.csv-selected) {
    box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.4), var(--shadow-md);
  }

  :global(.node-group.csv-selected) .node-label {
    color: var(--success);
  }
</style>