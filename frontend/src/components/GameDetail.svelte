<script lang="ts">
  import type { GameDetail } from "../types";
  import { fetchGame } from "../api";
  import { esc } from "../utils";

  interface Props {
    id: number;
  }

  let { id }: Props = $props();

  let data = $state<GameDetail | null>(null);
  let loading = $state(true);

  async function loadGame(): Promise<void> {
    loading = true;
    try {
      data = await fetchGame(id);
    } finally {
      loading = false;
    }
  }

  async function copyText(text: string): Promise<void> {
    await navigator.clipboard.writeText(text);
  }

  $effect(() => {
    void loadGame();
  });
</script>

{#if loading}
  <p style="color:var(--muted);font-size:12px;padding:4px 0">Cargando…</p>
{:else if data}
  {@const mesas = data.mesas ?? []}
  {@const waiting = data.waiting_list ?? []}
  <div class="panel-scroll">
    <div class="section">
      <div class="section-title">Resumen</div>
      <div class="meta-grid">
        <span class="meta-key">Generado</span>
        <span class="meta-val">{esc(data.created_at)}</span>
        <span class="meta-key">Intentos</span>
        <span class="meta-val">{data.intentos}</span>
        <span class="meta-key">Snapshot entrada</span>
        <span class="meta-val">#{data.input_snapshot_id}</span>
        <span class="meta-key">Snapshot salida</span>
        <span class="meta-val">#{data.output_snapshot_id}</span>
      </div>
    </div>
    <div class="section">
      <button class="copy-btn" onclick={() => copyText(data?.copypaste ?? "")}
        >📋 Copiar lista para compartir</button
      >
      <div class="share-pre" style="margin-top:8px">{esc(data?.copypaste)}</div>
    </div>
    {#if mesas.length > 0}
      <div class="section">
        <div class="section-title">Partidas ({mesas.length})</div>
        {#each mesas as mesa (mesa.numero)}
          {@const playersTxt = mesa.jugadores.map((j) => j.nombre).join("\n")}
          <div class="mesa-card">
            <div class="mesa-header">
              <span class="mesa-title">Partida {mesa.numero}</span>
              {#if mesa.gm}
                <span class="gm-tag gm-tag-ok">GM: {esc(mesa.gm)}</span>
              {:else}
                <span class="gm-tag gm-tag-bad">⚠️ Sin GM</span>
              {/if}
            </div>
            <ul class="player-list">
              {#each mesa.jugadores as j, i}
                <li>
                  <span class="p-num">{i + 1}.</span>
                  <span class="p-name">{esc(j.nombre)}</span>
                  {#if j.etiqueta === "Nuevo"}
                    <span class="tag tag-nuevo">Nuevo</span>
                  {:else}
                    <span class="tag tag-antiguo">{esc(j.etiqueta)}</span>
                  {/if}
                </li>
              {/each}
            </ul>
            <button
              class="copy-btn"
              style="margin-top:9px"
              onclick={() => copyText(playersTxt)}>📋 Copiar jugadores</button
            >
          </div>
        {/each}
      </div>
    {/if}
    {#if waiting.length > 0}
      {@const waitTxt = waiting.map((w) => w.nombre).join("\n")}
      <div class="section">
        <div class="section-title">Lista de espera</div>
        {#each waiting as w}
          <div class="waiting-item">
            <span class="waiting-name">{esc(w.nombre)}</span>
            <span class="waiting-cupos">{esc(w.cupos)}</span>
          </div>
        {/each}
        <button class="copy-btn" onclick={() => copyText(waitTxt)}
          >📋 Copiar lista de espera</button
        >
      </div>
    {/if}
  </div>
{/if}

<style>
  .section {
    margin-bottom: 22px;
  }

  .section-title {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: var(--muted);
    margin-bottom: 10px;
  }

  .meta-grid {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 4px 14px;
    font-size: 12px;
  }

  .meta-key {
    color: var(--muted);
    font-weight: 500;
  }

  .meta-val {
    font-weight: 600;
  }

  .copy-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 8px 14px;
    width: 100%;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    border: 1px solid var(--border);
    background: var(--surface2);
    color: var(--text);
    transition: background 0.15s;
  }

  .copy-btn:hover {
    background: var(--border);
  }

  :global(.copy-btn.ok) {
    background: var(--success);
    color: #fff;
    border-color: var(--success);
  }

  .share-pre {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px;
    font-size: 12px;
    font-family: "SF Mono", Menlo, monospace;
    white-space: pre-wrap;
    max-height: 200px;
    overflow-y: auto;
    color: var(--text);
  }

  .mesa-card {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 9px;
    padding: 11px 13px;
    margin-bottom: 10px;
  }

  .mesa-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
  }

  .mesa-title {
    font-weight: 700;
    font-size: 13px;
  }

  .gm-tag {
    font-size: 11px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 99px;
  }

  .gm-tag-ok {
    color: var(--report-dark);
    background: var(--report-bg);
    border: 1px solid var(--report-border);
  }

  .gm-tag-bad {
    color: #92400e;
    background: #fffbeb;
    border: 1px solid var(--pending-border);
  }

  .player-list {
    list-style: none;
  }

  .player-list li {
    font-size: 12px;
    padding: 4px 0;
    display: flex;
    align-items: center;
    gap: 8px;
    border-bottom: 1px solid var(--border);
  }

  .player-list li:last-child {
    border-bottom: none;
  }

  .p-num {
    color: var(--muted);
    font-size: 11px;
    min-width: 16px;
  }

  .p-name {
    flex: 1;
    font-weight: 500;
  }

  .tag {
    font-size: 10px;
    padding: 1px 6px;
    border-radius: 4px;
    font-weight: 600;
    white-space: nowrap;
  }

  .tag-nuevo {
    background: #fef9c3;
    color: #713f12;
  }

  .tag-antiguo {
    background: #f0fdf4;
    color: #166534;
  }

  .waiting-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 7px 10px;
    background: #fffbeb;
    border: 1px solid #fde68a;
    border-radius: 7px;
    margin-bottom: 6px;
    font-size: 12px;
  }

  .waiting-name {
    font-weight: 600;
  }

  .waiting-cupos {
    color: #92400e;
    font-size: 11px;
  }
</style>
