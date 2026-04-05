<script lang="ts">
  import type { HistoryLog } from "../types";
  import { formatAction, formatDate } from "../i18n";

  interface Props {
    history: HistoryLog[];
  }

  let { history }: Props = $props();
</script>

{#if history && history.length > 0}
  <details style="margin: 0 18px;">
    <summary
      class="section-title"
      style="
      cursor: pointer; 
      padding: 8px 0; 
      border-top: 1px solid var(--border);
      margin: 0;
      list-style: none;
      transition: background-color 0.15s ease;
      user-select: none;
    "
      onmouseenter={(e) => {
        const target = e.target as HTMLElement;
        if (target) {
          target.style.backgroundColor = "var(--surface2)";
          target.style.paddingLeft = "4px";
          target.style.paddingRight = "4px";
          target.style.marginLeft = "-4px";
          target.style.marginRight = "-4px";
        }
      }}
      onmouseleave={(e) => {
        const target = e.target as HTMLElement;
        if (target) {
          target.style.backgroundColor = "transparent";
          target.style.paddingLeft = "0";
          target.style.paddingRight = "0";
          target.style.marginLeft = "0";
          target.style.marginRight = "0";
        }
      }}
    >
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
                  .map((r) => `${r.from} ➔ ${r.to}`)
                  .join(", ")}
              </div>
            {/if}
            {#if log.changes.modified.length > 0}
              <div class="change-modified">
                <div style="margin-bottom: 2px;">✏️ Editados:</div>
                <ul class="mod-list">
                  {#each log.changes.modified as mod (mod.nombre)}
                    <li>
                      <span class="mod-name">{mod.nombre}:</span>
                      {#each Object.entries(mod.changes) as [field, vals] (field)}
                        <span class="mod-detail"
                          >[{field}: {vals.old} ➔ {vals.new}]</span
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
  .section-title {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: var(--muted);
    margin-bottom: 10px;
  }

  .history-list {
    list-style: none;
    padding: 0;
    margin: 0 18px 16px;
    max-height: 25vh;
    overflow-y: auto;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--surface);
  }

  .history-item {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 8px 12px;
    border-bottom: 1px solid var(--border);
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
    color: var(--accent);
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
    padding: 0 0 0 8px;
    margin: 0;
    border-left: 2px solid var(--border);
  }
  .mod-list li {
    margin-bottom: 2px;
  }
  .mod-name {
    font-weight: 600;
  }
  .mod-detail {
    color: var(--muted);
    font-size: 10px;
    margin-left: 4px;
  }
</style>
