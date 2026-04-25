<script lang="ts">
  import PanelSection from "./PanelSection.svelte";

  interface Props {
    class?: string;
  }

  let { class: className = "" }: Props = $props();
</script>

<PanelSection class={className}>
  <div data-testid="test-child">Child Content</div>
</PanelSection>
