<script lang="ts">
  import type { SyncEdge } from "../types";

  interface Props {
    node: SyncEdge;
  }

  let { node }: Props = $props();

  let date = $derived((node.created_at || "").split(" ")[0] ?? "");
</script>

<div class="node node-sync" data-id={node.id} data-type="sync">
  <div class="node-icon">☁️</div>
  <div class="node-label">Sync Notion</div>
  <div class="node-name">{date}</div>
  <div class="node-meta">#{node.from_id} → #{node.to_id}</div>
</div>