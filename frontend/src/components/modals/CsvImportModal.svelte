<script lang="ts">
  import Button from "../ui/Button.svelte";

  interface Props {
    onImport: (text: string) => void;
    onCancel: () => void;
  }

  let { onImport, onCancel }: Props = $props();

  let csvText = $state("");

  function autofocus(node: HTMLTextAreaElement) {
    node.focus();
  }

  function handleImport(): void {
    onImport(csvText);
    csvText = "";
  }

  function handleCancel(): void {
    onCancel();
    csvText = "";
  }
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="modal-overlay" onclick={handleCancel}>
  <div class="modal-content" onclick={(e) => e.stopPropagation()}>
    <div class="modal-title">Pegar CSV</div>
    <p class="modal-description">
      Pega el contenido CSV con las columnas: nombre, is_new, juegos_este_ano,
      prioridad, partidas_deseadas, partidas_gm
    </p>
    <textarea
      use:autofocus
      bind:value={csvText}
      placeholder="nombre,is_new,juegos_este_ano,prioridad,partidas_deseadas,partidas_gm&#10;Alice,Nuevo,0,false,1,0&#10;Bob,Antiguo,3,true,2,1"
      rows="10"
    ></textarea>
    <div class="modal-actions">
      <Button variant="secondary" onclick={handleCancel}>Cancelar</Button>
      <Button variant="primary" onclick={handleImport}>Importar</Button>
    </div>
  </div>
</div>

<style>
  /* Ensure modal is properly positioned above all content */
  .modal-overlay {
    position: fixed;
    inset: 0;
    background: var(--modal-backdrop);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    backdrop-filter: blur(2px);
  }

  .modal-content {
    background: var(--bg-secondary);
    border: 1px solid var(--border-subtle);
    border-radius: var(--space-16);
    padding: var(--space-24);
    width: 100%;
    max-width: calc(var(--space-8) * 62);
    max-height: 80vh;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: var(--space-16);
  }

  .modal-title {
    font-size: 16px;
    font-weight: 700;
  }

  .modal-description {
    font-size: 12px;
    color: var(--text-muted);
  }

  .modal-content textarea {
    width: 100%;
    border: 1px solid var(--border-subtle);
    border-radius: var(--space-8);
    padding: var(--space-16);
    font-family: monospace;
    font-size: 12px;
    background: var(--bg-tertiary);
    color: var(--text-primary);
    resize: vertical;
    flex-grow: 1;
  }

  .modal-content textarea:focus {
    outline: 1px solid var(--border-focus);
    border-color: var(--border-focus);
  }

  .modal-actions {
    display: flex;
    gap: var(--space-8);
    justify-content: flex-end;
  }
</style>
