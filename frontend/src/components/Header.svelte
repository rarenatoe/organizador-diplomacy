<script lang="ts">
  import {
    getSelectedSnapshot,
    getSyncButtonEnabled,
    getOrganizarEnabled,
    getOrganizarLabel,
    deselectSnapshot,
  } from "../stores.svelte";

  interface Props {
    onrefresh: () => void;
    onsync: () => void;
    onorganizar: () => void;
    syncing: boolean;
    running: boolean;
  }

  let { onrefresh, onsync, onorganizar, syncing, running }: Props = $props();

  let disabled = $derived(syncing || running);
  let syncButtonEnabled = $derived(getSyncButtonEnabled());
  let organizarEnabled = $derived(getOrganizarEnabled());
  let organizarLabel = $derived(getOrganizarLabel());
</script>

<header>
  <h1>🎲 Organizador Diplomacy <span id="pending-badge">⏳ Sin jugar</span></h1>
  <button class="btn btn-secondary" id="btn-refresh" onclick={onrefresh}
    >⟳ Actualizar</button
  >
  <button
    class="btn btn-secondary"
    id="btn-sync"
    onclick={onsync}
    disabled={!syncButtonEnabled || disabled}
    title={!syncButtonEnabled ? "Selecciona un snapshot en la cadena para sincronizar desde ese punto" : ""}
    >↻ Sync Notion</button
  >
  <button
    class="btn btn-primary"
    id="btn-organizar"
    onclick={onorganizar}
    disabled={!organizarEnabled || disabled}
    title={!organizarEnabled ? "Selecciona un snapshot en la cadena para organizar" : ""}
    >▶ <span id="organizar-label">{organizarLabel}</span></button
  >
  {#if getSelectedSnapshot() !== null}
    <button
      class="btn btn-ghost"
      id="btn-deselect"
      title="Volver al CSV más reciente"
      onclick={deselectSnapshot}>✕</button
    >
  {/if}
</header>

<style>
  header {
    height: var(--hdr);
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    padding: 0 20px;
    gap: 10px;
    box-shadow: var(--shadow);
    flex-shrink: 0;
    z-index: 10;
  }

  header h1 {
    font-size: 17px;
    font-weight: 700;
    flex: 1;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  #pending-badge {
    font-size: 11px;
    font-weight: 600;
    background: #fef3c7;
    color: #92400e;
    border: 1px solid var(--pending-border);
    padding: 2px 8px;
    border-radius: 99px;
    display: none;
  }

  :global(#pending-badge.visible) {
    display: inline-block;
  }
</style>
