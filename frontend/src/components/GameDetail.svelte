<script lang="ts">
  import type { GameDetail, DraftResponse, DraftPlayer } from "../types";
  import { fetchGame } from "../api";
  import { esc } from "../utils";
  import { translateCountry, getCountryEmoji } from "../i18n";
  import Button from "./Button.svelte";
  import PanelLayout from "./PanelLayout.svelte";

  interface Props {
    id: number;
    openGameDraft: (
      snapshotId: number,
      draft: DraftResponse,
      gameId: number,
    ) => void;
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
      pais_reason: player.pais_reason || null,
    };
  }

  function getTableCopyText(table: any): string {
    const footnotes: Record<string, string> = {};
    let footnoteCounter = 0;

    // Build player lines and collect footnotes
    const playerLines: string[] = [];
    let index = 1;
    for (const player of table.jugadores) {
      let line = `${index}. ${player.nombre}`;
      if (player.pais) {
        const translated = translateCountry(player.pais);
        if (player.pais_reason) {
          // Get or create footnote marker
          if (!footnotes[player.pais_reason]) {
            footnoteCounter++;
            footnotes[player.pais_reason] = "*".repeat(footnoteCounter);
          }
          const marker = footnotes[player.pais_reason];
          line += ` (${translated}${marker})`;
        } else {
          line += ` (${translated})`;
        }
      }
      playerLines.push(line);
      index++;
    }

    // Build footnote lines
    const footnoteLines: string[] = [];
    for (const [reason, marker] of Object.entries(footnotes)) {
      footnoteLines.push(`${marker} ${reason}`);
    }

    // Combine all lines
    const allLines = [...playerLines];
    if (footnoteLines.length > 0) {
      allLines.push("");
      allLines.push(...footnoteLines);
    }

    return allLines.join("\n");
  }

  function getFullShareText(gameData: GameDetail | null): string {
    if (!gameData) return "";

    const lines: string[] = [];

    // Add tables
    if (gameData.mesas && gameData.mesas.length > 0) {
      for (const table of gameData.mesas) {
        lines.push(`Partida ${table.numero}`);
        if (table.gm) {
          lines.push(`GM: ${table.gm}`);
        }

        // Add players
        for (const player of table.jugadores) {
          let playerLine = `- ${player.nombre}`;
          if (player.pais) {
            const translated = translateCountry(player.pais);
            playerLine += ` (${translated})`;
          }
          lines.push(playerLine);
        }

        lines.push(""); // Empty line between tables
      }
    }

    // Add waiting list
    if (gameData.waiting_list && gameData.waiting_list.length > 0) {
      lines.push("Lista de espera:");
      for (const waiter of gameData.waiting_list) {
        lines.push(`- ${waiter.nombre} (${waiter.cupos})`);
      }
    }

    return lines.join("\n").trim();
  }

  $effect(() => {
    void loadGame();
  });
</script>

{#snippet gameFooter()}
  <Button
    variant="primary"
    fill={true}
    icon="✏️"
    onclick={() => {
      const draft = {
        mesas:
          (data?.mesas ?? []).map((m) => ({
            numero: m.numero,
            gm: m.gm
              ? mapToDraftPlayer({ nombre: m.gm, experiencia: "Antiguo" })
              : null,
            jugadores: m.jugadores.map(mapToDraftPlayer),
          })) || [],
        tickets_sobrantes:
          (data?.waiting_list ?? []).map(mapToDraftPlayer) || [],
        minimo_teorico: 0,
        intentos_usados: data?.intentos || 0,
      };
      openGameDraft(data!.input_snapshot_id, draft, id);
    }}>Editar Jornada</Button
  >
{/snippet}

{#if loading}
  <p style="color:var(--muted);font-size:12px;padding:4px 0">Cargando…</p>
{:else if data}
  {@const mesas = data.mesas ?? []}
  {@const waiting = data.waiting_list ?? []}
  <PanelLayout footer={gameFooter}>
    {#snippet body()}
      <div class="section">
        <div class="section-title">Resumen</div>
        <div class="meta-grid">
          <span class="meta-key">Generado</span>
          <span class="meta-val">{esc(data?.created_at)}</span>
          <span class="meta-key">Intentos</span>
          <span class="meta-val">{data?.intentos}</span>
          <span class="meta-key">Snapshot entrada</span>
          <span class="meta-val">#{data?.input_snapshot_id}</span>
          <span class="meta-key">Snapshot salida</span>
          <span class="meta-val">#{data?.output_snapshot_id}</span>
        </div>
      </div>
      <div class="section">
        <Button
          size="sm"
          variant={copiedId === "share" ? "success" : "secondary"}
          icon={copiedId === "share" ? "✅" : "📋"}
          fill={true}
          onclick={() => copyText(getFullShareText(data), "share")}
          >{copiedId === "share"
            ? "Copiado"
            : "Copiar lista para compartir"}</Button
        >
      </div>
      {#if mesas.length > 0}
        <div class="section">
          <div class="section-title">Partidas ({mesas.length})</div>
          {#each mesas as table (table.numero)}
            {@const playersTxt = getTableCopyText(table)}
            <div class="mesa-card">
              <div class="mesa-header">
                <span class="mesa-title">Partida {table.numero}</span>
                {#if table.gm}
                  <span class="gm-tag gm-tag-ok">GM: {esc(table.gm)}</span>
                {:else}
                  <span class="gm-tag gm-tag-bad">⚠️ Sin GM</span>
                {/if}
              </div>
              <ul class="player-list">
                {#each table.jugadores as player, i (player.nombre)}
                  <li>
                    <span class="p-num">{i + 1}.</span>
                    <span class="p-name"
                      >{esc(player.nombre)}
                      {player.pais ? getCountryEmoji(player.pais) : ""}
                      {#if player.pais_reason}
                        <span class="reason-tooltip">
                          <span class="info-icon">ℹ️</span>
                          <span class="tooltip-popover"
                            >{player.pais_reason}</span
                          >
                        </span>
                      {/if}</span
                    >
                    {#if player.etiqueta === "Nuevo"}
                      <div class="tag-wrapper">
                        <span class="tag tag-nuevo">Nuevo</span>
                      </div>
                    {:else}
                      <div class="tag-wrapper">
                        <span class="tag tag-antiguo"
                          >{esc(player.etiqueta)}</span
                        >
                      </div>
                    {/if}
                  </li>
                {/each}
              </ul>
              <Button
                size="sm"
                variant={copiedId === "players-" + table.numero
                  ? "success"
                  : "secondary"}
                icon={copiedId === "players-" + table.numero ? "✅" : "📋"}
                class={copiedId === "players-" + table.numero ? "ok" : ""}
                fill={true}
                onclick={() => copyText(playersTxt, "players-" + table.numero)}
                >{copiedId === "players-" + table.numero
                  ? "Copiado"
                  : "Copiar jugadores"}</Button
              >
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
          <Button
            size="sm"
            variant={copiedId === "waiting" ? "success" : "secondary"}
            icon={copiedId === "waiting" ? "✅" : "📋"}
            fill={true}
            onclick={() => copyText(waitTxt, "waiting")}
            >{copiedId === "waiting"
              ? "Copiado"
              : "Copiar lista de espera"}</Button
          >
        </div>
      {/if}
    {/snippet}
  </PanelLayout>
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
    display: grid;
    grid-template-columns: 16px 1fr 120px;
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
    overflow: visible;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-weight: 500;
  }

  .tag-wrapper {
    display: flex;
    justify-content: flex-end;
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
    display: grid;
    grid-template-columns: 1fr 60px;
    align-items: center;
    padding: 7px 10px;
    background: #fffbeb;
    border: 1px solid #fde68a;
    border-radius: 7px;
    margin-bottom: 6px;
    font-size: 12px;
  }

  .waiting-name {
    font-weight: 600;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .waiting-cupos {
    color: #92400e;
    font-size: 11px;
    text-align: right;
  }

  .reason-tooltip {
    position: relative;
    display: inline-flex;
    align-items: center;
    cursor: help;
    margin-left: 4px;
  }

  .info-icon {
    font-size: 11px;
    opacity: 0.7;
    transition: opacity 0.15s;
  }

  .reason-tooltip:hover .info-icon {
    opacity: 1;
  }

  .tooltip-popover {
    display: none;
    position: absolute;
    bottom: 100%;
    left: 50%;
    transform: translateX(-50%);
    background: #1f2937;
    color: #f9fafb;
    padding: 6px 10px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 500;
    white-space: normal;
    width: max-content;
    max-width: 220px;
    z-index: 9999;
    margin-bottom: 6px;
    box-shadow: var(--shadow-md);
    text-align: center;
    line-height: 1.4;
  }

  /* Little triangle pointer for the tooltip */
  .tooltip-popover::after {
    content: "";
    position: absolute;
    top: 100%;
    left: 50%;
    margin-left: -4px;
    border-width: 4px;
    border-style: solid;
    border-color: #1f2937 transparent transparent transparent;
  }

  .reason-tooltip:hover .tooltip-popover {
    display: block;
  }
</style>
