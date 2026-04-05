<script lang="ts">
  import type { DraftResponse, DraftPlayer } from "../types";
  import { fetchGameDraft, saveGameDraft } from "../api";
  import { setActiveNodeId } from "../stores.svelte";
  import { findLatestGameId } from "../snapshotUtils";
  import Button from "./Button.svelte";
  import PanelLayout from "./PanelLayout.svelte";
  import Badge from "./Badge.svelte";
  import Tooltip from "./Tooltip.svelte";
  import GameTableCard from "./GameTableCard.svelte";

  interface Props {
    snapshotId: number;
    onClose: () => void;
    onCancel: () => void;
    onChainUpdate: () => void;
    onOpenGame: (id: number) => void;
    onShowError: (title: string, output: string) => void;
    editingGameId?: number | null;
    initialDraft?: DraftResponse | null;
  }

  let {
    snapshotId,
    onClose,
    onCancel,
    onChainUpdate,
    onOpenGame,
    onShowError,
    editingGameId,
    initialDraft,
  }: Props = $props();

  let draftData = $state<DraftResponse | null>(null);
  let loading = $state(true);
  let saving = $state(false);

  type SwapTarget =
    | { type: "table"; tableIndex: number; playerIndex: number }
    | { type: "waiting"; playerIndex: number };
  let selectedSwap = $state<SwapTarget | null>(null);

  async function loadDraft(): Promise<void> {
    loading = true;
    try {
      if (initialDraft) {
        draftData = initialDraft;
      } else {
        const response = await fetchGameDraft(snapshotId);
        if (response.error) {
          onShowError("Error al generar draft", response.error);
          return;
        }
        draftData = response;
      }
    } catch (e) {
      onShowError("Error de conexión", String(e));
    } finally {
      loading = false;
    }
  }

  function handleCountryChange(
    tableIndex: number,
    playerIndex: number,
    newCountry: string,
  ): void {
    if (!draftData) return;

    // Check if the new country is already assigned to another player in the same table
    const table = draftData.mesas[tableIndex];
    if (!table) return;

    const conflictingPlayer = table.jugadores.find(
      (j, idx) =>
        idx !== playerIndex && j.pais === newCountry && newCountry !== "",
    );

    if (conflictingPlayer) {
      // Automatically swap countries between the two players
      const conflictingPlayerIndex = table.jugadores.indexOf(conflictingPlayer);
      const currentPlayer = table.jugadores[playerIndex]!;
      const tempCountry = currentPlayer.pais;

      // Assign new country to current player
      if (newCountry !== "") {
        currentPlayer.pais = newCountry;
      } else {
        // Handle "Aleatorio" selection - remove country assignment
        currentPlayer.pais = "";
      }

      // Give old country to conflicting player
      const conflictingPlayerObj = table.jugadores[conflictingPlayerIndex];
      if (conflictingPlayerObj) {
        conflictingPlayerObj.pais = tempCountry;
      }
    } else {
      // Just assign country if no conflict
      const currentPlayer = table.jugadores[playerIndex]!;
      if (newCountry !== "") {
        currentPlayer.pais = newCountry;
      } else {
        currentPlayer.pais = "";
      }
    }
  }

  async function handleSaveDraft(): Promise<void> {
    if (!draftData) return;

    saving = true;
    try {
      // Strip empty pais/pais_reason before sending so the API receives clean data
      const cleanTables = draftData.mesas.map((table) => ({
        ...table,
        jugadores: table.jugadores.map(({ pais, pais_reason, ...rest }) => ({
          ...rest,
          pais: pais || "",
          ...(pais_reason ? { pais_reason } : {}),
        })),
      }));
      const cleanTicketsSobrantes = draftData.tickets_sobrantes.map(
        ({ pais, pais_reason, ...rest }) => ({
          ...rest,
          pais: pais || "",
          ...(pais_reason ? { pais_reason } : {}),
        }),
      );
      const payload: DraftResponse = {
        ...draftData,
        mesas: cleanTables,
        tickets_sobrantes: cleanTicketsSobrantes,
      };

      const response = await saveGameDraft({
        snapshot_id: snapshotId,
        draft: payload,
        editing_game_id: editingGameId || null,
      });
      if (response.error) {
        onShowError("Error al guardar draft", response.error);
        return;
      }

      // Close the draft panel and open the new game
      onClose();
      onChainUpdate();

      // Find and open the latest game
      const { fetchChain } = await import("../api");
      const chainData = await fetchChain();
      const gameId = findLatestGameId(chainData.roots);
      if (gameId !== null) {
        setActiveNodeId(gameId);
        onOpenGame(gameId);
      }
    } catch (e) {
      onShowError("Error de conexión", String(e));
    } finally {
      saving = false;
    }
  }

  function handlePlayerClick(target: SwapTarget): void {
    if (!draftData) return;

    if (selectedSwap === null) {
      // First selection - set the swap target
      selectedSwap = target;
    } else {
      // Second selection - attempt to swap
      if (
        selectedSwap.type === target.type &&
        selectedSwap.type === "table" &&
        target.type === "table" &&
        selectedSwap.tableIndex === target.tableIndex &&
        selectedSwap.playerIndex === target.playerIndex
      ) {
        // Clicked the same player - cancel selection
        selectedSwap = null;
        return;
      }

      // Get the two players to swap
      let playerA: DraftPlayer | null = null;
      let playerB: DraftPlayer | null = null;

      // Extract Player A
      if (selectedSwap.type === "table") {
        const tableAIndex = selectedSwap.tableIndex;
        const tableA = draftData.mesas[tableAIndex];
        if (tableA) {
          playerA = tableA.jugadores[selectedSwap.playerIndex] ?? null;
        }
      } else {
        playerA = draftData.tickets_sobrantes[selectedSwap.playerIndex] ?? null;
      }

      // Extract Player B
      if (target.type === "table") {
        const tableBIndex = target.tableIndex;
        const tableB = draftData.mesas[tableBIndex];
        if (tableB) {
          playerB = tableB.jugadores[target.playerIndex] ?? null;
        }
      } else {
        playerB = draftData.tickets_sobrantes[target.playerIndex] ?? null;
      }

      if (!playerA || !playerB) {
        onShowError(
          "Error",
          "No se encontraron los jugadores para intercambiar.",
        );
        selectedSwap = null;
        return;
      }

      // Constraint: Check for duplicates in destination tables
      if (target.type === "table") {
        const tableAIndex = target.tableIndex;
        const tableA = draftData.mesas[tableAIndex];
        if (tableA) {
          const hasDuplicate = tableA.jugadores.some(
            (p) => p.nombre === playerA.nombre && p !== playerA,
          );
          if (hasDuplicate) {
            onShowError(
              "Movimiento Inválido",
              `El jugador ${playerA.nombre} ya está en la mesa ${tableA.numero}.`,
            );
            selectedSwap = null;
            return;
          }
        }
      }

      if (selectedSwap.type === "table") {
        const tableBIndex = selectedSwap.tableIndex;
        const tableB = draftData.mesas[tableBIndex];
        if (tableB) {
          const hasDuplicate = tableB.jugadores.some(
            (p) => p.nombre === playerB.nombre && p !== playerB,
          );
          if (hasDuplicate) {
            onShowError(
              "Movimiento Inválido",
              `El jugador ${playerB.nombre} ya está en la mesa ${tableB.numero}.`,
            );
            selectedSwap = null;
            return;
          }
        }
      }

      // Execute the swap
      if (selectedSwap.type === "table") {
        const selectedTableIndex = selectedSwap.tableIndex;
        const selectedPlayerIndex = selectedSwap.playerIndex;

        if (target.type === "table") {
          // Mesa to Mesa swap
          const targetTableIndex = target.tableIndex;
          const targetPlayerIndex = target.playerIndex;

          if (
            draftData.mesas[selectedTableIndex]?.jugadores[
              selectedPlayerIndex
            ] &&
            draftData.mesas[targetTableIndex]?.jugadores[targetPlayerIndex]
          ) {
            // Swap countries so slot retains assigned country
            const tempPais =
              draftData.mesas[selectedTableIndex].jugadores[selectedPlayerIndex]
                .pais;
            const targetPais =
              draftData.mesas[targetTableIndex].jugadores[targetPlayerIndex]
                .pais;

            draftData.mesas[selectedTableIndex].jugadores[
              selectedPlayerIndex
            ].pais = targetPais;
            draftData.mesas[targetTableIndex].jugadores[
              targetPlayerIndex
            ].pais = tempPais;

            draftData.mesas[selectedTableIndex].jugadores[selectedPlayerIndex] =
              playerB;
            draftData.mesas[targetTableIndex].jugadores[targetPlayerIndex] =
              playerA;
          }
        } else {
          // Mesa to Espera swap
          const targetPlayerIndex = target.playerIndex;

          if (
            draftData.mesas[selectedTableIndex]?.jugadores[
              selectedPlayerIndex
            ] &&
            draftData.tickets_sobrantes[targetPlayerIndex] !== undefined
          ) {
            // Swap countries so slot retains assigned country
            const tempPais =
              draftData.mesas[selectedTableIndex].jugadores[selectedPlayerIndex]
                .pais;
            const targetPais =
              draftData.tickets_sobrantes[targetPlayerIndex].pais;

            draftData.mesas[selectedTableIndex].jugadores[
              selectedPlayerIndex
            ].pais = targetPais;
            draftData.tickets_sobrantes[targetPlayerIndex].pais = tempPais;

            draftData.mesas[selectedTableIndex].jugadores[selectedPlayerIndex] =
              playerB;
            draftData.tickets_sobrantes[targetPlayerIndex] = playerA;
          }
        }
      } else {
        const selectedPlayerIndex = selectedSwap.playerIndex;

        if (target.type === "table") {
          // Espera to Mesa swap
          const targetTableIndex = target.tableIndex;
          const targetPlayerIndex = target.playerIndex;

          if (
            draftData.tickets_sobrantes[selectedPlayerIndex] !== undefined &&
            draftData.mesas[targetTableIndex]?.jugadores[targetPlayerIndex]
          ) {
            // Swap countries so slot retains assigned country
            const tempPais =
              draftData.tickets_sobrantes[selectedPlayerIndex].pais;
            const targetPais =
              draftData.mesas[targetTableIndex].jugadores[targetPlayerIndex]
                .pais;

            draftData.tickets_sobrantes[selectedPlayerIndex].pais = targetPais;
            draftData.mesas[targetTableIndex].jugadores[
              targetPlayerIndex
            ].pais = tempPais;

            draftData.tickets_sobrantes[selectedPlayerIndex] = playerB;
            draftData.mesas[targetTableIndex].jugadores[targetPlayerIndex] =
              playerA;
          }
        } else {
          // Espera to Espera swap
          const targetPlayerIndex = target.playerIndex;

          if (
            draftData.tickets_sobrantes[selectedPlayerIndex] !== undefined &&
            draftData.tickets_sobrantes[targetPlayerIndex] !== undefined
          ) {
            // Swap countries so slot retains assigned country
            const tempPais =
              draftData.tickets_sobrantes[selectedPlayerIndex].pais;
            const targetPais =
              draftData.tickets_sobrantes[targetPlayerIndex].pais;

            draftData.tickets_sobrantes[selectedPlayerIndex].pais = targetPais;
            draftData.tickets_sobrantes[targetPlayerIndex].pais = tempPais;

            draftData.tickets_sobrantes[selectedPlayerIndex] = playerB;
            draftData.tickets_sobrantes[targetPlayerIndex] = playerA;
          }
        }
      }

      // Reset selection
      selectedSwap = null;
    }
  }

  function isSelectedSwap(target: SwapTarget): boolean {
    if (!selectedSwap) return false;
    if (selectedSwap.type !== target.type) return false;

    if (selectedSwap.type === "table" && target.type === "table") {
      return (
        selectedSwap.tableIndex === target.tableIndex &&
        selectedSwap.playerIndex === target.playerIndex
      );
    } else if (selectedSwap.type === "waiting" && target.type === "waiting") {
      return selectedSwap.playerIndex === target.playerIndex;
    }
    return false;
  }

  loadDraft();
</script>

<PanelLayout>
  {#snippet body()}
    {#if loading}
      <p style="color:var(--muted);font-size:12px;padding:4px 0">
        Generando draft...
      </p>
    {:else if draftData}
      <div class="section">
        <div class="section-title">
          Draft de Partidas - Snapshot #{snapshotId}
        </div>
        <div class="meta-grid">
          <span class="meta-key">Mesas generadas</span>
          <span class="meta-val">{draftData.mesas.length}</span>
          <span class="meta-key">Jugadores en espera</span>
          <span class="meta-val">{draftData.tickets_sobrantes.length}</span>
          <span class="meta-key">Intentos usados</span>
          <span class="meta-val">{draftData.intentos_usados}</span>
        </div>
      </div>
      {#if draftData.mesas.length > 0}
        <div class="section">
          <div class="section-title">Partidas ({draftData.mesas.length})</div>
          {#each draftData.mesas as table, tableIndex (table.numero)}
            <GameTableCard
              tableNumber={table.numero}
              gmName={table.gm ? table.gm.nombre : null}
            >
              <ul class="player-list">
                {#each table.jugadores as j, i (j.nombre)}
                  {@const target = {
                    type: "table" as const,
                    tableIndex,
                    playerIndex: i,
                  }}
                  {@const isSelected = isSelectedSwap(target)}
                  <li class:swapping-active={isSelected}>
                    <span class="p-num">{i + 1}.</span>
                    <span class="p-name">{j.nombre}</span>
                    <div class="country-container">
                      <select
                        class="country-select"
                        value={j.pais || ""}
                        onchange={(e) => {
                          const target = e.target as HTMLSelectElement;
                          handleCountryChange(tableIndex, i, target.value);
                        }}
                      >
                        <option value="">🎲 Aleatorio</option>
                        <option value="England">🇬🇧 Inglaterra</option>
                        <option value="France">🇫🇷 Francia</option>
                        <option value="Germany">🇩🇪 Alemania</option>
                        <option value="Italy">🇮🇹 Italia</option>
                        <option value="Austria">🇦🇹 Austria</option>
                        <option value="Russia">🇷🇺 Rusia</option>
                        <option value="Turkey">🇹🇷 Turquía</option>
                      </select>
                      {#if j.pais_reason}
                        <Tooltip text={j.pais_reason} />
                      {/if}
                    </div>
                    <div class="tag-wrapper">
                      {#if j.es_nuevo}
                        <Badge
                          variant="warning"
                          text="Nuevo"
                          fixedWidth={true}
                        />
                      {:else}
                        <Badge
                          variant="success"
                          text="Antiguo"
                          fixedWidth={true}
                        />
                      {/if}
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      iconOnly={true}
                      icon="🔄"
                      title="Intercambiar"
                      onclick={() => handlePlayerClick(target)}
                    />
                  </li>
                {/each}
              </ul>
            </GameTableCard>
          {/each}
        </div>
      {/if}
      {#if draftData.tickets_sobrantes.length > 0}
        <div class="section">
          <div class="section-title">Lista de espera</div>
          {#each draftData.tickets_sobrantes as w, i (w.nombre)}
            {@const target = { type: "waiting" as const, playerIndex: i }}
            {@const isSelected = isSelectedSwap(target)}
            <div class="waiting-item" class:swapping-active={isSelected}>
              <span class="waiting-name">{w.nombre}</span>
              <span class="waiting-cupos">{w.partidas_deseadas} cupos</span>
              <Button
                variant="ghost"
                size="sm"
                iconOnly={true}
                icon="🔄"
                title="Intercambiar"
                onclick={() => handlePlayerClick(target)}
              />
            </div>
          {/each}
        </div>
      {/if}
    {:else}
      <p style="color:var(--danger);font-size:12px;padding:4px 0">
        No se pudo generar el draft
      </p>
    {/if}
  {/snippet}

  {#snippet footer()}
    {#if draftData}
      <Button
        variant="secondary"
        fill={true}
        onclick={onCancel}
        disabled={saving}>Cancelar</Button
      >
      <Button
        variant="primary"
        fill={true}
        icon={saving ? "⏳" : "✨"}
        onclick={handleSaveDraft}
        disabled={saving}
        >{saving ? "Guardando..." : "Confirmar y Guardar"}</Button
      >
    {/if}
  {/snippet}
</PanelLayout>

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

  .player-list {
    list-style: none;
  }

  .player-list li {
    font-size: 12px;
    padding: 4px 0;
    display: grid;
    grid-template-columns: 16px 1fr 115px 56px 32px;
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
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-weight: 500;
  }

  .tag-wrapper {
    display: flex;
    justify-content: center;
  }

  .country-container {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .country-select {
    font-size: 11px;
    padding: 2px 4px;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: var(--bg);
    color: var(--text);
    cursor: pointer;
    width: 100%;
    min-width: 0;
  }

  .swapping-active {
    background: #eff6ff;
    outline: 1px solid var(--accent);
    border-radius: 4px;
  }

  .waiting-item {
    display: grid;
    grid-template-columns: 1fr 60px 32px;
    align-items: center;
    padding: 7px 10px;
    background: #fffbeb;
    border: 1px solid #fde68a;
    border-radius: 7px;
    margin-bottom: 6px;
    font-size: 12px;
  }

  .waiting-item.swapping-active {
    background: #eff6ff;
    outline: 1px solid var(--accent);
    border-color: var(--accent);
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
</style>
