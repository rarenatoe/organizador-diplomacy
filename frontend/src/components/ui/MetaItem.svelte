<script lang="ts">
  import type { Snippet } from "svelte";

  interface Props {
    label: string;
    value?: string | number | null;
    children?: Snippet;
  }

  let { label, value, children }: Props = $props();
</script>

<span class="meta-key">{label}</span>
<span class="meta-val">
  {#if value !== undefined && value !== null}
    {value}
  {/if}
  {#if children}
    {@render children()}
  {/if}
</span>

<style>
  .meta-key {
    color: var(--text-muted);
    font-weight: 500;
  }

  .meta-val {
    font-weight: 600;
  }
</style>
