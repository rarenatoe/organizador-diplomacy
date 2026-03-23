<script lang="ts">
  import type { Snippet } from "svelte";

  interface Props {
    title: string;
    open: boolean;
    onclose: () => void;
    children: Snippet;
  }

  let { title, open, onclose, children }: Props = $props();
</script>

<aside class="panel" class:open>
  <div class="panel-inner">
    <div class="panel-header">
      <h2 id="panel-title">{title}</h2>
      <button class="btn btn-ghost" id="btn-close-panel" onclick={onclose}
        >✕</button
      >
    </div>
    <div class="panel-body" id="panel-body">
      {@render children()}
    </div>
  </div>
</aside>