<script lang="ts">
  import type { SimilarName, ResolutionAction, MergePair } from "../types";

  interface Props {
    visible: boolean;
    pairs: SimilarName[];
    oncomplete: (merges: MergePair[]) => void;
    oncancel: () => void;
  }

  let { visible, pairs, oncomplete, oncancel }: Props = $props();

  let currentIndex = $state(0);
  let decisions = $state<{ pair: SimilarName; action: ResolutionAction }[]>([]);

  let currentPair = $derived(pairs[currentIndex]);
  let total = $derived(pairs.length);
  let similarity = $derived(currentPair ? Math.round(currentPair.similarity * 100) : 0);

  function esc(s: string): string {
    const el = document.createElement("span");
    el.textContent = s;
    return el.innerHTML;
  }

  function handleAction(action: ResolutionAction): void {
    if (!currentPair) return;
    decisions = [...decisions, { pair: currentPair, action }];

    if (currentIndex < pairs.length - 1) {
      currentIndex++;
    } else {
      const merges: MergePair[] = decisions
        .filter((d) => d.action === "merge")
        .map((d) => ({ from: d.pair.snapshot, to: d.pair.notion }));
      oncomplete(merges);
    }
  }

  function handleStop(): void {
    oncancel();
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
      <div class="resolution-counter">Conflicto {currentIndex + 1} de {total}</div>
      {#if currentPair}
        <div class="resolution-pair">
          <div class="resolution-side">
            <span class="resolution-label">Notion</span>
            <span class="resolution-name resolution-name-notion"
              >{esc(currentPair.notion)}</span
            >
          </div>
          <div class="resolution-vs">vs</div>
          <div class="resolution-side">
            <span class="resolution-label">Snapshot</span>
            <span class="resolution-name resolution-name-snapshot"
              >{esc(currentPair.snapshot)}</span
            >
          </div>
        </div>
        <div class="resolution-similarity">{similarity}% similar</div>
        <div class="resolution-actions">
          <button
            class="btn btn-primary resolution-btn-merge"
            onclick={() => handleAction("merge")}>🔀 Fusionar</button
          >
          <button
            class="btn btn-secondary resolution-btn-skip"
            onclick={() => handleAction("skip")}>⏭ Omitir</button
          >
        </div>
      {/if}
      <div class="resolution-footer">
        <button class="btn btn-ghost resolution-btn-stop" onclick={handleStop}
          >Detener resolución</button
        >
      </div>
    </div>
  </div>
{/if}