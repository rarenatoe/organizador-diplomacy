<script lang="ts">
  import {
    apiGame,
    type GameDetailResponse,
    type GameDraftPlayer,
    type GameDraftResponseOutput,
    type GameDraftTableOutput,
  } from "../../generated-api";
  import { translateCountry, getCountryEmoji } from "../../i18n";
  import Button from "../ui/Button.svelte";
  import PanelLayout from "../layout/PanelLayout.svelte";
  import Badge from "../ui/Badge.svelte";
  import Tooltip from "../ui/Tooltip.svelte";
  import PlayerName from "../ui/PlayerName.svelte";
  import GameTableCard from "./GameTableCard.svelte";
  import SectionTitle from "../ui/SectionTitle.svelte";
  import CardGrid from "../layout/CardGrid.svelte";
  import CardGridItem from "../layout/CardGridItem.svelte";

  interface Props {
    id: number;
    onOpenGameDraft: (
      snapshotId: number,
      draft: GameDraftResponseOutput,
      gameId: number,
    ) => void;
  }

  let { id, onOpenGameDraft }: Props = $props();

  let gameDetail = $state<GameDetailResponse | undefined>(undefined);
  let loading = $state(true);
  let copiedId = $state<string | null>(null);

  async function loadGame(): Promise<void> {
    loading = true;
    try {
      const { data } = await apiGame({ path: { game_event_id: id } });
      gameDetail = data;
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

  function mapToDraftPlayer(player: GameDraftPlayer): GameDraftPlayer {
    return {
      nombre: player.nombre,
      is_new: player.is_new ?? false,
      juegos_este_ano: player.juegos_este_ano ?? 0,
      has_priority: player.has_priority ?? false,
      partidas_deseadas: player.partidas_deseadas ?? 1,
      partidas_gm: player.partidas_gm ?? 0,
      c_england: player.c_england ?? 0,
      c_france: player.c_france ?? 0,
      c_germany: player.c_germany ?? 0,
      c_italy: player.c_italy ?? 0,
      c_austria: player.c_austria ?? 0,
      c_russia: player.c_russia ?? 0,
      c_turkey: player.c_turkey ?? 0,
      country: player.country || { name: "", reason: "" },
    };
  }

  function getTableCopyText(table: GameDraftTableOutput): string {
    const footnotes: Record<string, string> = {};
    let footnoteCounter = 0;

    // Build player lines and collect footnotes
    const playerLines: string[] = [];
    let index = 1;
    for (const player of table.jugadores) {
      let line = `${index}. ${player.nombre}`;
      if (player.country) {
        const translated = translateCountry(player.country.name);
        if (player.country.reason) {
          // Get or create footnote marker
          if (!footnotes[player.country.reason]) {
            footnoteCounter++;
            footnotes[player.country.reason] = "*".repeat(footnoteCounter);
          }
          const marker = footnotes[player.country.reason];
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

  function getFullShareText(gameData: GameDetailResponse | null): string {
    if (!gameData) return "";

    const lines: string[] = [];

    // Add tables
    if (gameData.mesas && gameData.mesas.length > 0) {
      for (const table of gameData.mesas) {
        lines.push(`Partida ${table.numero}`);
        if (table.gm) {
          lines.push(`GM: ${table.gm.nombre}`);
        }

        // Add players
        for (const player of table.jugadores) {
          let playerLine = `- ${player.nombre}`;
          if (player.country) {
            const translated = translateCountry(player.country.name);
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
        lines.push(`- ${waiter.nombre} (${waiter.cupos_faltantes} cupos)`);
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
      const draft: GameDraftResponseOutput = {
        mesas:
          (gameDetail?.mesas ?? []).map((m) => ({
            numero: m.numero,
            gm: m.gm ? mapToDraftPlayer(m.gm) : null,
            jugadores: m.jugadores.map(mapToDraftPlayer),
          })) || [],
        tickets_sobrantes:
          (gameDetail?.waiting_list ?? []).map(mapToDraftPlayer) || [],
        minimo_teorico: 0,
        intentos_usados: gameDetail?.intentos || 0,
      };
      if (!gameDetail) {
        throw new Error("Game data is required for editing");
      }
      onOpenGameDraft(gameDetail.input_snapshot_id || 0, draft, id);
    }}>Editar Jornada</Button
  >
{/snippet}

{#if loading}
  <p class="loading-text">Cargando…</p>
{:else if gameDetail}
  {@const mesas = gameDetail.mesas ?? []}
  {@const waiting = gameDetail.waiting_list ?? []}
  <PanelLayout footer={gameFooter}>
    {#snippet body()}
      <div class="section">
        <SectionTitle title="Resumen" />
        <div class="meta-grid">
          <span class="meta-key">Generado</span>
          <span class="meta-val">{gameDetail?.created_at}</span>
          <span class="meta-key">Intentos</span>
          <span class="meta-val">{gameDetail?.intentos}</span>
          <span class="meta-key">Snapshot entrada</span>
          <span class="meta-val">#{gameDetail?.input_snapshot_id}</span>
          <span class="meta-key">Snapshot salida</span>
          <span class="meta-val">#{gameDetail?.output_snapshot_id}</span>
        </div>
      </div>
      <div class="section">
        <Button
          size="sm"
          variant={copiedId === "share" ? "success" : "secondary"}
          icon={copiedId === "share" ? "✅" : "📋"}
          fill={true}
          onclick={() =>
            copyText(getFullShareText(gameDetail || null), "share")}
          >{copiedId === "share"
            ? "Copiado"
            : "Copiar lista para compartir"}</Button
        >
      </div>
      {#if mesas.length > 0}
        <div class="section">
          <SectionTitle title="Partidas" count={mesas.length} />
          <CardGrid>
            {#each mesas as table (table.numero)}
              {@const playersTxt = getTableCopyText(table)}
              <CardGridItem>
                <GameTableCard
                  tableNumber={table.numero}
                  gmName={table.gm?.nombre || null}
                >
                  <ul class="player-list">
                    {#each table.jugadores as player, i (player.nombre)}
                      <li>
                        <span class="p-num">{i + 1}.</span>
                        <PlayerName
                          {player}
                          compact={true}
                          showNotionIndicator={false}
                        />
                        <div class="country-cell">
                          {#if player.country}
                            <span
                              class="country-text"
                              title={translateCountry(player.country.name)}
                            >
                              {getCountryEmoji(player.country.name)}
                              {translateCountry(player.country.name)}
                            </span>
                          {/if}
                        </div>
                        <div class="tooltip-cell">
                          {#if player.country?.reason}
                            <Tooltip text={player.country.reason} icon="ℹ️" />
                          {/if}
                        </div>
                        <div class="tag-wrapper">
                          <Tooltip
                            text={player.is_new
                              ? "Sin partidas previas"
                              : `${player.juegos_este_ano} juegos este año`}
                          >
                            <Badge
                              variant={player.is_new ? "warning" : "success"}
                              text={player.is_new ? "Nuevo" : "Antiguo"}
                              fixedWidth={true}
                            />
                          </Tooltip>
                        </div>
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
                    onclick={() =>
                      copyText(playersTxt, "players-" + table.numero)}
                    >{copiedId === "players-" + table.numero
                      ? "Copiado"
                      : "Copiar jugadores"}</Button
                  >
                </GameTableCard>
              </CardGridItem>
            {/each}
          </CardGrid>
        </div>
      {/if}
      {#if waiting.length > 0}
        {@const waitTxt = waiting.map((w) => w.nombre).join("\n")}
        <div class="section">
          <SectionTitle title="Lista de espera" />
          {#each waiting as w (w.nombre)}
            <div class="waiting-item">
              <PlayerName
                player={w}
                compact={true}
                showNotionIndicator={false}
              />
              <span class="waiting-cupos">{w.cupos_faltantes} cupo(s)</span>
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
    display: flex;
    flex-direction: column;
    gap: var(--space-16);
    margin-bottom: var(--space-24);
  }

  .meta-grid {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: var(--space-4) var(--space-16);
    font-size: 12px;
  }

  .meta-key {
    color: var(--text-muted);
    font-weight: 500;
  }

  .meta-val {
    font-weight: 600;
  }

  .player-list {
    list-style: none;
  }

  .player-list li {
    font-size: 12px;
    padding: var(--space-4) 0;
    display: grid;
    /* num (24) | name (minmax) | country (85px) | tooltip (24) | badge (80) */
    grid-template-columns:
      var(--space-24) minmax(0, 1fr) 85px var(--space-24)
      80px;
    align-items: center;
    gap: var(--space-8);
    border-bottom: 1px solid var(--border-subtle);
    width: 100%;
  }

  .country-cell {
    display: flex;
    align-items: center;
    min-width: 0;
    overflow: hidden;
  }

  .country-text {
    font-size: 11px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .tooltip-cell {
    display: flex;
    justify-content: center;
    align-items: center;
    width: 100%;
    height: 100%;
  }

  .player-list li:last-child {
    border-bottom: none;
  }

  .p-num {
    color: var(--text-muted);
    font-size: 11px;
    min-width: var(--space-16);
  }

  .tag-wrapper {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: var(--space-8);
  }

  .waiting-item {
    display: grid;
    grid-template-columns: 1fr var(--space-56);
    align-items: center;
    padding: var(--space-4) var(--space-8);
    background: var(--warning-bg-subtle);
    border: 1px solid var(--warning-border-subtle);
    border-radius: var(--space-8);
    margin-bottom: var(--space-4);
    font-size: 12px;
  }

  .waiting-cupos {
    color: var(--warning-text-subtle);
    font-size: 11px;
    text-align: right;
  }
</style>
