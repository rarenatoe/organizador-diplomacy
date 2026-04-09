<script lang="ts">
  interface Props {
    title: string;
    count?: number;
    class?: string;
    style?: string;
  }

  let { title, count, class: className = "", style = "" }: Props = $props();
</script>

<div class="section-title {className}" {style}>
  {title}
  {#if count !== undefined}
    ({count})
  {/if}
</div>

<style>
  .section-title {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: var(--text-muted);
  }
</style>
