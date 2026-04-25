<script lang="ts">
  import MetaGrid from "./MetaGrid.svelte";

  interface Props {
    class?: string;
  }

  let { class: className = "" }: Props = $props();
</script>

<MetaGrid class={className}>
  <div data-testid="test-child">Child Content</div>
</MetaGrid>
