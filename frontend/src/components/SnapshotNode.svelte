<script lang="ts">
  import type { SnapshotNode } from "../types";
  import GameNode from "./GameNode.svelte";
  import SyncNode from "./SyncNode.svelte";
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