<script lang="ts">
  import type { SimilarName, ResolutionAction, MergePair } from "../../types";
  import Badge from "../ui/Badge.svelte";
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
        .map((d) => {
          let toName = d.pair.notion_name;
          if (d.action === "use_existing" && d.pair.existing_local_name) {
            toName = d.pair.existing_local_name;
          }
          return {
            from: d.pair.snapshot,
            to: toName,
            action: d.action,
            notion_id: d.pair.notion_id,
          };
        });
      onComplete(merges);
    }
  }

  function handleStop(): void {
    onCancel();
  }

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
        <span class="resolution-icon">⚠️</span>
        <span class="resolution-title">Resolver Conflictos</span>
        <span class="resolution-counter">
          Conflicto {currentIndex + 1} de {total}
        </span>
      </div>
      {#if currentPair}
        <div class="comparison-card">
          <span class="side-label notion-label">Notion</span>
          <div class="vs-divider">VS</div>
          <span class="side-label snapshot-label">Snapshot</span>

          <span
            class="side-name highlight-notion notion-name"
            title={currentPair.notion_name}>{currentPair.notion_name}</span
          >
          <span
            class="side-name highlight-snapshot snapshot-name"
            title={currentPair.snapshot}>{currentPair.snapshot}</span
          >

          {#if currentPair.matched_alias}
            <span
              class="alias-text notion-alias"
              title={`(vía alias: ${currentPair.matched_alias})`}
            >
              (vía alias: {currentPair.matched_alias})</span
            >
          {/if}
        </div>

        <div class="resolution-similarity">
          <Badge
            variant="warning"
            text={`${similarity}% similar`}
            pill={true}
          />
        </div>

        {#if currentPair.existing_local_name}
          <div class="resolution-message">
            Jugador existente detectado. ¿Deseas usar <span
              class="highlight-snapshot">{currentPair.existing_local_name}</span
            >?
          </div>
          <div class="resolution-actions">
            <Button
              variant="primary"
              title={`Usar el jugador existente: ${currentPair.existing_local_name}`}
              onclick={() => handleAction("use_existing")}
              icon="✨">Usar {currentPair.existing_local_name}</Button
            >
            <Button
              variant="ghost"
              title="No realizar ninguna acción"
              onclick={() => handleAction("skip")}
              icon="⏭">Añadir sin vincular</Button
            >
          </div>
          <div class="compact-hint">
            <span class="hint-icon">💡</span>
            <div class="hint-text">
              <strong>Autocorrección:</strong> Evita duplicados usando el jugador
              que ya está en la lista.
            </div>
          </div>
        {:else}
          <div class="resolution-message">
            Encontramos a <span class="highlight-snapshot"
              >{currentPair.snapshot}</span
            >. Coincide con el jugador de Notion
            <span class="highlight-notion">{currentPair.notion_name}</span>
            {#if currentPair.matched_alias}<span class="alias-text"
                >(vía alias: {currentPair.matched_alias})</span
              >{/if}
          </div>
          <div class="resolution-actions">
            <Button
              variant="primary"
              title="Vincular y actualizar el nombre local al de Notion"
              onclick={() => handleAction("link_rename")}
              icon="📋">Vincular & Renombrar</Button
            >
            <Button
              variant="secondary"
              title="Vincular manteniendo el nombre local actual"
              onclick={() => handleAction("link_only")}
              icon="🔗">Vincular Solo</Button
            >
            <Button
              variant="ghost"
              title="No realizar ninguna acción"
              onclick={() => handleAction("skip")}
              icon="⏭">Añadir sin vincular</Button
            >
          </div>
          <div class="compact-hint">
            <span class="hint-icon">💡</span>
            <div class="hint-text">
              <strong>Vincular Solo</strong> conserva tu nombre local.<br />
              <strong>Renombrar</strong> usa el nombre de Notion.
            </div>
          </div>
        {/if}
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
    z-index: 1000;
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
    gap: var(--space-12);
    border: 1px solid var(--border-subtle);
  }

  .resolution-header {
    display: flex;
    align-items: center;
    gap: var(--space-8);
  }

  .resolution-icon {
    font-size: 1.5em;
  }

  .resolution-title {
    font-weight: 700;
    font-size: 1.1em;
    flex: 1;
  }

  .resolution-counter {
    color: var(--text-subtle);
    font-size: 0.9em;
    font-weight: 600;
  }

  .comparison-card {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
    grid-template-rows: auto auto auto;
    row-gap: 2px;
    align-items: center;
    background: var(--bg-tertiary);
    border: 1px solid var(--border-subtle);
    border-radius: var(--space-8);
    padding: var(--space-12) var(--space-16);
    box-shadow: var(--shadow-sm);
  }

  .notion-label {
    grid-column: 1;
    grid-row: 1;
    text-align: right;
  }

  .snapshot-label {
    grid-column: 3;
    grid-row: 1;
    text-align: left;
  }

  .vs-divider {
    grid-column: 2;
    grid-row: 2;
    font-size: 11px;
    font-weight: 800;
    color: var(--text-muted);
    padding: 0 var(--space-16);
    text-transform: uppercase;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .notion-name {
    grid-column: 1;
    grid-row: 2;
    text-align: right;
  }

  .snapshot-name {
    grid-column: 3;
    grid-row: 2;
    text-align: left;
  }

  .notion-alias {
    grid-column: 1;
    grid-row: 3;
    text-align: right;
    font-size: 11px;
    color: var(--text-muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .side-label {
    font-size: 10px;
    font-weight: 700;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .side-name {
    font-size: 15px;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .resolution-similarity {
    display: flex;
    justify-content: center;
    margin-bottom: var(--space-4);
  }

  .resolution-message {
    font-size: 13px;
    line-height: 1.5;
    color: var(--text-secondary);
    text-align: center;
  }

  .highlight-snapshot {
    font-weight: 600;
    color: var(--success-text-subtle);
  }

  .highlight-notion {
    font-weight: 600;
    color: var(--info-text-subtle);
  }

  .alias-text {
    color: var(--text-muted);
    font-style: italic;
  }

  .resolution-actions {
    display: flex;
    flex-direction: column;
    gap: var(--space-8);
  }

  .compact-hint {
    display: flex;
    align-items: center;
    gap: var(--space-8);
    background: var(--info-bg-subtle);
    border: 1px solid var(--info-border-subtle);
    padding: var(--space-8) var(--space-12);
    border-radius: var(--space-8);
  }

  .hint-icon {
    font-size: 14px;
    line-height: 1.2;
  }

  .hint-text {
    font-size: 11px;
    color: var(--info-text-subtle);
    line-height: 1.4;
  }

  .resolution-footer {
    display: flex;
    justify-content: center;
    padding-top: var(--space-12);
    border-top: 1px solid var(--border-subtle);
  }
</style>
