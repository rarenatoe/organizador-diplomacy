<script lang="ts">
  import type { PlayerSimilarityItem } from "../../generated-api";
  import type { MergePair, ResolutionAction } from "../../syncResolution";
  import Badge from "../ui/Badge.svelte";
  import Button from "../ui/Button.svelte";

  interface Props {
    visible: boolean;
    pairs: Array<PlayerSimilarityItem>;
    onComplete: (merges: MergePair[]) => void;
    onCancel: () => void;
  }

  let { visible, pairs, onComplete, onCancel }: Props = $props();

  let currentIndex = $state(0);
  let selectedMatchIndex = $state(0);
  let decisions = $state<
    { pair: PlayerSimilarityItem; action: ResolutionAction }[]
  >([]);

  // Group the flat pairs array by the snapshot name
  let groupedConflicts = $derived.by(() => {
    const groups: Record<string, PlayerSimilarityItem[]> = {};
    for (const pair of pairs) {
      if (!groups[pair.snapshot]) {
        groups[pair.snapshot] = [];
      }
      groups[pair.snapshot]?.push(pair);
    }
    return Object.values(groups);
  });

  let total = $derived(groupedConflicts.length);
  let currentGroup = $derived(groupedConflicts[currentIndex]);
  let currentSelectedPair = $derived(
    currentGroup ? currentGroup[selectedMatchIndex] : undefined,
  );

  function handleAction(action: ResolutionAction): void {
    if (!currentSelectedPair) return;

    // Record the decision for the currently selected radio option
    decisions = [...decisions, { pair: currentSelectedPair, action }];

    let nextIndex = currentIndex + 1;

    if (nextIndex < total) {
      // Move to the next grouped conflict and reset the radio selection
      currentIndex = nextIndex;
      selectedMatchIndex = 0;
    } else {
      // Finished resolving all groups
      const merges: MergePair[] = decisions
        .filter((d) => d.action !== "skip")
        .map((d) => {
          let toName = d.pair.notion_name;
          // If we chose to use the existing local, map 'to' to that local name
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
      selectedMatchIndex = 0;
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

      {#if currentGroup && currentSelectedPair}
        <div class="resolution-message">
          Coincidencias para: <span class="highlight-snapshot"
            >{currentGroup[0]?.snapshot}</span
          >
        </div>

        <div class="options-list">
          {#each currentGroup as match, i (match.notion_id)}
            <label
              class="match-option"
              class:selected={selectedMatchIndex === i}
            >
              <input type="radio" bind:group={selectedMatchIndex} value={i} />
              <div class="match-info">
                <div class="match-info-header">
                  <span class="notion-name highlight-notion"
                    >{match.notion_name}</span
                  >
                  <Badge
                    variant="warning"
                    text={`${Math.round(match.similarity * 100)}%`}
                    pill={true}
                  />
                </div>
                {#if match.matched_alias}
                  <span
                    class="alias-text"
                    title={`(vía alias: ${match.matched_alias})`}
                  >
                    (vía alias: {match.matched_alias})
                  </span>
                {/if}
                {#if match.existing_local_name}
                  <div class="existing-badge">
                    ✨ Jugador existente ({match.existing_local_name})
                  </div>
                {/if}
              </div>
            </label>
          {/each}
        </div>

        <div class="dynamic-actions">
          {#if currentSelectedPair.existing_local_name}
            <Button
              variant="primary"
              title={`Usar el jugador existente: ${currentSelectedPair.existing_local_name}`}
              onclick={() => handleAction("use_existing")}
              icon="✨">Usar {currentSelectedPair.existing_local_name}</Button
            >
            <div class="compact-hint">
              <span class="hint-icon">💡</span>
              <div class="hint-text">
                <strong>Autocorrección:</strong> Evita duplicados vinculando al jugador
                que ya está en tu base local.
              </div>
            </div>
          {:else}
            <div class="button-row">
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
            </div>
            <div class="compact-hint">
              <span class="hint-icon">💡</span>
              <div class="hint-text">
                <strong>Vincular Solo</strong> conserva tu nombre local.<br />
                <strong>Renombrar</strong> usa el nombre de Notion.
              </div>
            </div>
          {/if}
          <div class="skip-row">
            <Button
              variant="ghost"
              title="Ignorar Notion y añadir como jugador nuevo"
              onclick={() => handleAction("skip")}
              icon="⏭">Añadir sin vincular</Button
            >
          </div>
        </div>
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
    max-width: calc(var(--space-8) * 56);
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

  .resolution-message {
    font-size: 14px;
    line-height: 1.5;
    color: var(--text-secondary);
    text-align: center;
    margin-bottom: var(--space-4);
  }

  .highlight-snapshot {
    font-weight: 600;
    color: var(--success-text-subtle);
  }

  .highlight-notion {
    font-weight: 600;
    color: var(--info-text-subtle);
  }

  /* --- Radio List Styles --- */
  .options-list {
    display: flex;
    flex-direction: column;
    gap: var(--space-8);
    max-height: 250px;
    overflow-y: auto;
    padding-right: var(--space-4); /* Prevents scrollbar from hugging content */
  }

  .options-list::-webkit-scrollbar {
    width: 6px;
  }
  .options-list::-webkit-scrollbar-thumb {
    background-color: var(--border-muted);
    border-radius: 4px;
  }

  .match-option {
    display: flex;
    align-items: flex-start;
    gap: var(--space-12);
    padding: var(--space-12);
    background: var(--bg-tertiary);
    border: 1px solid var(--border-subtle);
    border-radius: var(--space-8);
    cursor: pointer;
    transition: all 0.2s;
    user-select: none;
  }

  .match-option:hover {
    border-color: var(--border-muted);
  }

  .match-option.selected {
    background: var(--info-bg-subtle);
    border-color: var(--info-border-subtle);
  }

  .match-option input[type="radio"] {
    margin-top: var(--space-4);
    accent-color: var(--info-text-subtle);
    cursor: pointer;
  }

  .match-info {
    display: flex;
    flex-direction: column;
    gap: 4px;
    flex: 1;
  }

  .match-info-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .notion-name {
    font-size: 14px;
  }

  .alias-text {
    font-size: 11px;
    color: var(--text-muted);
    font-style: italic;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .existing-badge {
    font-size: 11px;
    font-weight: 600;
    color: var(--success-text-subtle);
    background: var(--success-bg-subtle);
    padding: 2px 6px;
    border-radius: 4px;
    display: inline-block;
    width: fit-content;
    margin-top: 2px;
  }

  /* --- Dynamic Actions Styles --- */
  .dynamic-actions {
    display: flex;
    flex-direction: column;
    gap: var(--space-8);
    margin-top: var(--space-4);
  }

  .button-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--space-8);
  }

  .skip-row {
    display: flex;
    justify-content: center;
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
