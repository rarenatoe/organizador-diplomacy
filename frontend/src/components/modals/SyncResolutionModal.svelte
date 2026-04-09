<script lang="ts">
  import type { SimilarName, ResolutionAction, MergePair } from "../../types";
  import Button from "../ui/Button.svelte";

  interface Props {
    visible: boolean;
    pairs: SimilarName[];
    onComplete: (merges: MergePair[]) => void;
    onCancel: () => void;
  }

  let { visible, pairs, onComplete, onCancel }: Props = $props();

  let currentIndex = $state(0);
  let decisions = $state<{ pair: SimilarName; action: ResolutionAction }[]>([]);

  let currentPair = $derived(pairs[currentIndex]);
  let total = $derived(pairs.length);
  let similarity = $derived(
    currentPair ? Math.round(currentPair.similarity * 100) : 0,
  );

  function handleAction(action: ResolutionAction): void {
    if (!currentPair) return;
    decisions = [...decisions, { pair: currentPair, action }];

    if (currentIndex < pairs.length - 1) {
      currentIndex++;
    } else {
      const merges: MergePair[] = decisions
        .filter((d) => d.action !== "skip")
        .map((d) => ({
          from: d.pair.snapshot,
          to: d.pair.notion,
          action: d.action,
        }));
      onComplete(merges);
    }
  }

  function handleStop(): void {
    onCancel();
  }

  // Reset state when modal becomes visible
  $effect(() => {
    if (visible) {
      currentIndex = 0;
      decisions = [];
    }
  });
</script>

{#if visible}
  <div class="resolution-overlay visible">
    <div class="resolution-card">
      <div class="resolution-header">
        <span class="resolution-icon">🔍</span>
        <span class="resolution-title">Nombres similares</span>
      </div>
      <div class="resolution-counter">
        Conflicto {currentIndex + 1} de {total}
      </div>
      {#if currentPair}
        <div class="resolution-pair">
          <div class="resolution-side">
            <span class="resolution-label">Notion</span>
            <span class="resolution-name resolution-name-notion"
              >{currentPair.notion}</span
            >
          </div>
          <div class="resolution-vs">vs</div>
          <div class="resolution-side">
            <span class="resolution-label">Snapshot</span>
            <span class="resolution-name resolution-name-snapshot"
              >{currentPair.snapshot}</span
            >
          </div>
        </div>
        <div class="resolution-similarity">{similarity}% similar</div>
        <div class="resolution-actions">
          <Button
            variant="primary"
            title="Fusionar y adoptar el nombre principal de Notion"
            onclick={() => handleAction("merge_notion")}
            icon="📋">Usar nombre Notion</Button
          >
          <Button
            variant="secondary"
            title="Fusionar manteniendo el nombre local actual"
            onclick={() => handleAction("merge_local")}
            icon="📱">Mantener local</Button
          >
          <Button
            variant="ghost"
            title="No realizar ninguna acción de fusión"
            onclick={() => handleAction("skip")}
            icon="⏭">Omitir</Button
          >
        </div>
        <p class="resolution-hint">
          💡 <strong>Mantener local</strong> vincula los datos pero conserva el nombre
          del snapshot. Recuerda actualizar el nombre o añadir el alias en Notion
          para futuras sincronizaciones.
        </p>
      {/if}
      <div class="resolution-footer">
        <Button variant="ghost" onclick={handleStop}>Detener resolución</Button>
      </div>
    </div>
  </div>
{/if}

<style>
  .resolution-overlay {
    position: fixed;
    inset: 0;
    background: var(--modal-backdrop);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 150;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.2s;
  }

  .resolution-overlay.visible {
    opacity: 1;
    pointer-events: all;
  }

  .resolution-card {
    background: var(--bg-secondary);
    border-radius: var(--space-16);
    padding: var(--space-24);
    width: 100%;
    max-width: calc(var(--space-8) * 52);
    box-shadow: var(--shadow-xl);
    display: flex;
    flex-direction: column;
    gap: var(--space-16);
  }

  .resolution-header {
    display: flex;
    align-items: center;
    gap: var(--space-8);
  }

  .resolution-icon {
    font-size: 20px;
  }

  .resolution-title {
    font-size: 15px;
    font-weight: 700;
    color: var(--text-primary);
  }

  .resolution-counter {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .resolution-pair {
    display: flex;
    align-items: center;
    gap: var(--space-16);
    background: var(--bg-tertiary);
    border: 1px solid var(--border-default);
    box-shadow: var(--shadow-sm);
    border-radius: var(--space-8);
    padding: var(--space-16);
  }

  .resolution-side {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: var(--space-8);
  }

  .resolution-label {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-muted);
  }

  .resolution-name {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
    word-break: break-word;
  }

  .resolution-name-notion {
    color: var(--info-text-subtle);
  }

  .resolution-name-snapshot {
    color: var(--success-text-subtle);
  }

  .resolution-vs {
    font-size: 11px;
    font-weight: 700;
    color: var(--text-muted);
    text-transform: uppercase;
    flex-shrink: 0;
  }

  .resolution-similarity {
    font-size: 12px;
    font-weight: 600;
    color: var(--warning-text-subtle);
    text-align: center;
  }

  .resolution-hint {
    font-size: 11px;
    line-height: var(--line-height-16);
    color: var(--text-muted);
    background: var(--bg-tertiary);
    padding: var(--space-8) var(--space-16);
    border-radius: var(--space-8);
    margin: 0;
    border-left: var(--space-4) solid var(--warning-border);
  }

  .resolution-actions {
    display: flex;
    flex-direction: column;
    gap: var(--space-8);
  }

  .resolution-footer {
    display: flex;
    justify-content: center;
  }
</style>
