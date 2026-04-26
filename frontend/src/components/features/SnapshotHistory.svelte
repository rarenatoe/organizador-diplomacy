<script lang="ts">
  import type { HistoryEntry } from "../../generated-api";
  import {
    formatAction,
    formatDate,
    translateField,
    translateValue,
  } from "../../i18n";

  let { history }: { history: HistoryEntry[] } = $props();
</script>

{#if history && history.length > 0}
  <details class="history-details">
    <summary class="section-title history-row">
      Historial de Cambios ({history.length})
    </summary>
    <ul class="history-list">
      {#each history as log (log.id)}
        <li class="history-item">
          <div class="history-header">
            <span class="history-type">{formatAction(log.action_type)}</span>
            <span class="history-date">{formatDate(log.created_at)}</span>
          </div>
          <div class="history-summary">
            {#if log.changes.added.length > 0}
              <div class="change-added">
                + Añadidos: {log.changes.added.join(", ")}
              </div>
            {/if}
            {#if log.changes.removed.length > 0}
              <div class="change-removed">
                - Removidos: {log.changes.removed.join(", ")}
              </div>
            {/if}
            {#if log.changes.renamed.length > 0}
              <div class="change-renamed">
                ✏️ Renombrados: {log.changes.renamed
                  .map((r) => `${r.old_name} ➔ ${r.new_name}`)
                  .join(", ")}
              </div>
            {/if}
            {#if log.changes.modified.length > 0}
              <div class="change-modified">
                <div class="modified-header">✏️ Editados:</div>
                <ul class="mod-list">
                  {#each log.changes.modified as mod (mod.nombre)}
                    <li>
                      <span class="mod-name">{mod.nombre}:</span>
                      {#each Object.entries(mod.changes) as [field, vals] (field)}
                        <span class="mod-detail"
                          >[{translateField(field)}: {translateValue(
                            field,
                            vals.old,
                          )} ➔ {translateValue(field, vals.new)}]</span
                        >
                      {/each}
                    </li>
                  {/each}
                </ul>
              </div>
            {/if}
            {#if log.changes.added.length === 0 && log.changes.removed.length === 0 && log.changes.renamed.length === 0 && log.changes.modified.length === 0}
              <div class="change-none">Sin cambios locales</div>
            {/if}
          </div>
        </li>
      {/each}
    </ul>
  </details>
{/if}

<style>
  .history-details {
    margin: 0 var(--space-16);
  }

  .modified-header {
    margin-bottom: var(--space-4);
  }

  .section-title {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: var(--muted);
    margin-bottom: var(--space-8);
  }

  .history-list {
    list-style: none;
    padding: 0;
    margin: 0 var(--space-16) var(--space-16);
    max-height: 25vh;
    overflow-y: auto;
    border: 1px solid var(--border-subtle);
    border-radius: var(--space-8);
    background: var(--surface);
  }

  .history-item {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
    padding: var(--space-8) var(--space-16);
    border-bottom: 1px solid var(--border-subtle);
  }

  .history-item:last-child {
    border-bottom: none;
  }

  .history-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .history-date {
    font-size: 10px;
    color: var(--muted);
    font-weight: 600;
  }

  .history-type {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--primary-border);
  }

  .history-summary {
    font-size: 11px;
    color: var(--text);
    line-height: 1.3;
  }

  .change-added {
    color: var(--success-dark);
    font-weight: 500;
  }
  .change-removed {
    color: var(--error-dark);
    font-weight: 500;
  }
  .change-renamed {
    color: var(--info-dark);
  }
  .change-modified {
    color: var(--text);
  }
  .change-none {
    color: var(--muted);
    font-style: italic;
  }
  .mod-list {
    list-style: none;
    padding: 0 0 0 var(--space-8);
    margin: 0;
    border-left: var(--space-4) solid var(--border-subtle);
  }
  .mod-list li {
    margin-bottom: var(--space-4);
  }
  .mod-name {
    font-weight: 600;
  }
  .mod-detail {
    color: var(--text-muted);
    font-size: 10px;
    margin-left: var(--space-4);
  }
  .history-row:hover {
    background: var(--bg-tertiary);
    padding-left: var(--space-4);
    padding-right: var(--space-4);
    margin-left: calc(-1 * var(--space-4));
    margin-right: calc(-1 * var(--space-4));
  }
</style>
