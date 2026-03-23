<script lang="ts">
  interface Props {
    visible: boolean;
    title: string;
    output: string;
    isError: boolean;
    loading: boolean;
    onclose: () => void;
  }

  let { visible, title, output, isError, loading, onclose }: Props = $props();
</script>

{#if visible}
  <div class="modal-overlay open">
    <div class="modal-box">
      <div class="modal-title">
        {#if loading}
          <span class="spinner"></span>
        {:else if isError}
          <span>❌</span>
        {:else}
          <span>✅</span>
        {/if}
        <span id="modal-title-text">{title}</span>
      </div>
      <div class="modal-out" class:err={isError} id="modal-out">{output}</div>
      <div class="modal-foot">
        <button class="btn btn-secondary" onclick={onclose} disabled={loading}
          >Cerrar</button
        >
      </div>
    </div>
  </div>
{/if}