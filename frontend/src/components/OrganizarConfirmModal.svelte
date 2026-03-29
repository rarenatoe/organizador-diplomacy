<script lang="ts">
  import type { OrganizarValidation } from "../types";
  import { esc } from "../utils";
  import Button from "./Button.svelte";

  interface Props {
    visible: boolean;
    validation: OrganizarValidation | null;
    onConfirm: () => void;
    onEdit: () => void;
    onCancel: () => void;
  }

  let { visible, validation, onConfirm, onEdit, onCancel }: Props = $props();

  let displayedExcluded = $derived(
    validation?.excludedPlayers.slice(0, 5) ?? [],
  );
  let extraCount = $derived((validation?.excludedPlayers.length ?? 0) - 5);
</script>

{#if visible && validation}
  <div class="confirm-overlay" class:visible>
    <div class="confirm-card">
      <div class="confirm-header">
        <span class="confirm-icon">⚠️</span>
        <span class="confirm-title">Revisar Roster</span>
      </div>

      <div class="confirm-body">
        {#if validation.isAllOnes}
          <div class="warning-item">
            <span class="warning-icon">⚠️</span>
            <p>
              Todos los jugadores tienen 1 partida deseada (posible lista sin
              editar).
            </p>
          </div>
        {/if}

        {#if validation.gmShortage}
          <div class="warning-item">
            <span class="warning-icon">⚠️</span>
            <p>
              Faltan GMs: Se proyectan {validation.gmShortage.required} partidas pero
              solo hay {validation.gmShortage.assigned} GM(s) asignado(s).
            </p>
          </div>
        {/if}

        {#if validation.excludedPlayers.length > 0}
          <div class="excluded-section">
            <div class="excluded-title">Jugadores excluidos (0 partidas):</div>
            <div class="excluded-list">
              {#each displayedExcluded as name (name)}
                <div class="excluded-item">{esc(name)}</div>
              {/each}
              {#if extraCount > 0}
                <div class="excluded-more">+ {extraCount} más</div>
              {/if}
            </div>
          </div>
        {/if}
      </div>

      <div class="confirm-actions">
        <Button variant="primary" onclick={onConfirm}>
          Organizar de todos modos
        </Button>
        <Button variant="secondary" onclick={onEdit}>Volver a Editar</Button>
        <Button variant="ghost" onclick={onCancel}>Cancelar</Button>
      </div>
    </div>
  </div>
{/if}

<style>
  .confirm-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.45);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 150;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.2s;
  }

  .confirm-overlay.visible {
    opacity: 1;
    pointer-events: all;
  }

  .confirm-card {
    background: var(--surface);
    border-radius: 14px;
    padding: 24px;
    width: 420px;
    max-width: 90vw;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.25);
    display: flex;
    flex-direction: column;
    gap: 16px;
    border: 1px solid var(--border);
  }

  .confirm-header {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .confirm-icon {
    font-size: 20px;
  }

  .confirm-title {
    font-size: 15px;
    font-weight: 700;
    color: var(--text);
  }

  .confirm-body {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .warning-item {
    display: flex;
    gap: 10px;
    background: #fffbeb;
    border: 1px solid #fde68a;
    border-radius: 8px;
    padding: 12px;
    color: #92400e;
    font-size: 13px;
    line-height: 1.4;
  }

  .warning-item .warning-icon {
    flex-shrink: 0;
  }

  .warning-item p {
    margin: 0;
    font-weight: 500;
  }

  .excluded-section {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px;
  }

  .excluded-title {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--muted);
    margin-bottom: 8px;
  }

  .excluded-list {
    max-height: 120px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .excluded-item {
    font-size: 13px;
    color: var(--text);
  }

  .excluded-more {
    font-size: 12px;
    color: var(--muted);
    font-style: italic;
    margin-top: 2px;
  }

  .confirm-actions {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-top: 8px;
  }
</style>
