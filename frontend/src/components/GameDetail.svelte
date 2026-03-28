<script lang="ts">
  import type { GameDetail, DraftResponse, DraftPlayer } from "../types";
  import { fetchGame } from "../api";
  import { esc } from "../utils";
  import Button from "./Button.svelte";

  interface Props {
    id: number;
    openGameDraft?: (snapshotId: number, draft: DraftResponse, gameId: number) => void;
  }

  let { id, openGameDraft }: Props = $props();

  let data = $state<GameDetail | null>(null);
  let loading = $state(true);
  let copiedId = $state<string | null>(null);

  async function loadGame(): Promise<void> {
    loading = true;
    try {
      data = await fetchGame(id);
    } finally {
      loading = false;
    }
  }

  async function copyText(text: string, buttonId: string): Promise<void> {
    await navigator.clipboard.writeText(text);
    copiedId = buttonId;
    setTimeout(() => {
      if (copiedId === buttonId) copiedId = null;
    }, 1500);
  }

  function getCountryEmoji(pais: string | undefined): string {
    // Handle both English (backend) and Spanish (display) country names
    const countryEmojis: Record<string, string> = {
      // English names (from backend)
      England: "🇬🇧",
      France: "🇫🇷",
      Germany: "🇩🇪",
      Italy: "🇮🇹",
      Austria: "🇦🇹",
      Russia: "🇷🇺",
      Turkey: "🇹🇷",
      // Spanish names (for display)
      Inglaterra: "🇬🇧",
      Francia: "🇫🇷",
      Alemania: "🇩🇪",
      Italia: "🇮🇹",
      Rusia: "🇷🇺",
      Turquía: "🇹🇷"
    };
    return pais ? (countryEmojis[pais] || "") : "";
  }

  function mapToDraftPlayer(player: any): DraftPlayer {
    return {
      nombre: player.nombre,
      es_nuevo: player.es_nuevo ?? false,
      juegos_ano: player.juegos_este_ano ?? 0,
      tiene_prioridad: player.prioridad === 1,
      partidas_deseadas: player.partidas_deseadas ?? 1,
      partidas_gm: player.partidas_gm ?? 0,
      c_england: player.c_england ?? 0,
      c_france: player.c_france ?? 0,
      c_germany: player.c_germany ?? 0,
      c_italy: player.c_italy ?? 0,
      c_austria: player.c_austria ?? 0,
      c_russia: player.c_russia ?? 0,
      c_turkey: player.c_turkey ?? 0,
      pais: player.pais || null,
    };
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
      <Button size="sm" variant={copiedId === 'share' ? 'success' : 'secondary'} icon={copiedId === 'share' ? "✅" : "📋"} fill={true} onclick={() => copyText(data?.copypaste ?? "", 'share')}>{copiedId === 'share' ? "Copiado" : "Copiar lista para compartir"}</Button>
      <div class="share-pre" style="margin-top:8px">{esc(data?.copypaste)}</div>
    </div>
    {#if mesas.length > 0}
      <div class="section">
        <div class="section-title">Partidas ({mesas.length})</div>
        {#each mesas as mesa (mesa.numero)}
          {@const playersTxt = mesa.jugadores.map((j) => j.pais ? `${j.nombre} (${j.pais})` : j.nombre).join("\n")}
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
              {#each mesa.jugadores as j, i (j.nombre)}
                <li>
                  <span class="p-num">{i + 1}.</span>
                  <span class="p-name">{esc(j.nombre)} {j.pais ? getCountryEmoji(j.pais) : ""}</span>
                  {#if j.etiqueta === "Nuevo"}
                    <span class="tag tag-nuevo">Nuevo</span>
                  {:else}
                    <span class="tag tag-antiguo">{esc(j.etiqueta)}</span>
                  {/if}
                </li>
              {/each}
            </ul>
            <Button size="sm" variant={copiedId === 'players-' + mesa.numero ? 'success' : 'secondary'} icon={copiedId === 'players-' + mesa.numero ? "✅" : "📋"} class={copiedId === 'players-' + mesa.numero ? 'ok' : ''} fill={true} onclick={() => copyText(playersTxt, 'players-' + mesa.numero)}>{copiedId === 'players-' + mesa.numero ? "Copiado" : "Copiar jugadores"}</Button>
          </div>
        {/each}
      </div>
    {/if}
    {#if waiting.length > 0}
      {@const waitTxt = waiting.map((w) => w.nombre).join("\n")}
      <div class="section">
        <div class="section-title">Lista de espera</div>
        {#each waiting as w (w.nombre)}
          <div class="waiting-item">
            <span class="waiting-name">{esc(w.nombre)}</span>
            <span class="waiting-cupos">{esc(w.cupos)}</span>
          </div>
        {/each}
        <Button size="sm" variant={copiedId === 'waiting' ? 'success' : 'secondary'} icon={copiedId === 'waiting' ? "✅" : "📋"} fill={true} onclick={() => copyText(waitTxt, 'waiting')}>{copiedId === 'waiting' ? "Copiado" : "Copiar lista de espera"}</Button>
      </div>
    {/if}
    {#if openGameDraft}
    <div class="panel-footer">
      <Button variant="primary" fill={true} icon="✏️" onclick={() =>{
        const draft = { 
          mesas: (data?.mesas ?? []).map(m =>({ 
            numero: m.numero, 
            gm: m.gm ? mapToDraftPlayer({nombre: m.gm, experiencia: "Antiguo"}) : null, 
            jugadores: m.jugadores.map(mapToDraftPlayer) 
          })) || [], 
          tickets_sobrantes: (data?.waiting_list ?? []).map(mapToDraftPlayer) || [], 
          minimo_teorico: 0, 
          intentos_usados: data?.intentos || 0 
        };
        openGameDraft(data!.input_snapshot_id, draft, id);
      }}>Editar Jornada</Button>
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
