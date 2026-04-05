<script lang="ts">
  import Button from "./Button.svelte";

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
      Pega el contenido CSV con las columnas: nombre, experiencia,
      juegos_este_ano, prioridad, partidas_deseadas, partidas_gm
    </p>
    <textarea
      use:autofocus
      bind:value={csvText}
      placeholder="nombre,experiencia,juegos_este_ano,prioridad,partidas_deseadas,partidas_gm&#10;Alice,Nuevo,0,0,1,0&#10;Bob,Antiguo,3,1,2,1"
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
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px;
    max-width: 500px;
    width: 90%;
    max-height: 80vh;
    overflow-y: auto;
  }

  .modal-title {
    font-size: 16px;
    font-weight: 700;
    margin-bottom: 8px;
  }

  .modal-description {
    font-size: 12px;
    color: var(--muted);
    margin-bottom: 16px;
  }

  .modal-content textarea {
    width: 100%;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px;
    font-family: monospace;
    font-size: 12px;
    background: var(--surface2);
    color: var(--text);
    resize: vertical;
    margin-bottom: 16px;
  }

  .modal-content textarea:focus {
    outline: 2px solid var(--accent);
    border-color: transparent;
  }

  .modal-actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
  }
</style>
