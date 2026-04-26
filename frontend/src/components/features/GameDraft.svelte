<script lang="ts">
  import {
    apiChain,
    type GameDraftPlayer,
    type GameDraftResponseOutput,
  } from "../../generated-api";
  import { apiGameDraft, apiGameSave } from "../../generated-api/sdk.gen";
  import { findLatestGameId } from "../../snapshotUtils";
  import { setActiveNodeId } from "../../stores.svelte";
  import { parseApiError } from "../../utils";
  import CardGrid from "../layout/CardGrid.svelte";
  import CardGridItem from "../layout/CardGridItem.svelte";
  import PanelLayout from "../layout/PanelLayout.svelte";
  import PanelSection from "../layout/PanelSection.svelte";
  import Badge from "../ui/Badge.svelte";
  import Button from "../ui/Button.svelte";
  import MetaGrid from "../ui/MetaGrid.svelte";
  import MetaItem from "../ui/MetaItem.svelte";
  import PlayerName from "../ui/PlayerName.svelte";
  import SectionTitle from "../ui/SectionTitle.svelte";
  import Tooltip from "../ui/Tooltip.svelte";
  import GameTableCard from "./GameTableCard.svelte";
  import Waitlist from "./Waitlist.svelte";

  interface Props {
    snapshotId: number;
    onClose: () => void;
    onCancel: () => void;
    onChainUpdate: () => void;
    onOpenGame: (gameId: number) => void;
    onShowError: (title: string, output: string) => void;
    editingGameId?: number | null;
    initialDraft?: GameDraftResponseOutput | null;
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

  let draftData = $state<GameDraftResponseOutput | null>(null);
  let loading = $state(true);
  let saving = $state(false);

  type SwapTarget =
    | { type: "table"; tableIndex: number; playerIndex: number }
    | { type: "waiting"; playerIndex: number };
  let selectedSwap = $state<SwapTarget | null>(null);

  const COUNTRY_OPTIONS = [
    { value: "England", label: "🇬🇧 Inglaterra" },
    { value: "France", label: "🇫🇷 Francia" },
    { value: "Germany", label: "🇩🇪 Alemania" },
    { value: "Italy", label: "🇮🇹 Italia" },
    { value: "Austria", label: "🇦🇹 Austria" },
    { value: "Russia", label: "🇷🇺 Rusia" },
    { value: "Turkey", label: "🇹🇷 Turquía" },
  ];

  async function loadDraft(): Promise<void> {
    loading = true;
    try {
      if (initialDraft) {
        draftData = initialDraft;
      } else {
        const { data, error } = await apiGameDraft({
          body: { snapshot_id: snapshotId },
        });
        if (error) {
          onShowError("Error al generar draft", parseApiError(error));
          return;
        }
        draftData = data;
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
        idx !== playerIndex &&
        j.country?.name === newCountry &&
        newCountry !== "",
    );

    if (conflictingPlayer) {
      // Automatically swap the entire country object between the two players
      const conflictingPlayerIndex = table.jugadores.indexOf(conflictingPlayer);
      const currentPlayer = table.jugadores[playerIndex];
      if (!currentPlayer) {
        return;
      }

      const tempCountryObj = currentPlayer.country;

      // Assign the conflicting player's full country object (including reason) to current
      currentPlayer.country = conflictingPlayer.country;

      // Give old country object to conflicting player
      const conflictingPlayerObj = table.jugadores[conflictingPlayerIndex];
      if (conflictingPlayerObj) {
        conflictingPlayerObj.country = tempCountryObj;
      }
    } else {
      // Just assign country if no conflict and clear reason (since it's a fresh manual override)
      const currentPlayer = table.jugadores[playerIndex];
      if (!currentPlayer) {
        return;
      }
      currentPlayer.country =
        newCountry !== ""
          ? { name: newCountry, reason: "" }
          : { name: "", reason: "" };
    }
  }

  async function handleSaveDraft(): Promise<void> {
    if (!draftData) return;

    saving = true;
    try {
      // Strip empty country data before sending so the API receives clean data
      const cleanTables = draftData.mesas.map((table) => ({
        ...table,
        jugadores: table.jugadores.map(({ country, ...rest }) => ({
          ...rest,
          country: country?.name
            ? {
                name: country.name,
                reason: country.reason || "",
              }
            : { name: "", reason: "" },
        })),
      }));
      const cleanTicketsSobrantes = draftData.tickets_sobrantes.map(
        ({ country, ...rest }) => ({
          ...rest,
          country: country?.name
            ? {
                name: country.name,
                reason: country.reason || "",
              }
            : { name: "", reason: "" },
        }),
      );
      const payload: GameDraftResponseOutput = {
        ...draftData,
        mesas: cleanTables,
        tickets_sobrantes: cleanTicketsSobrantes,
      };

      const { error } = await apiGameSave({
        body: {
          snapshot_id: snapshotId,
          draft: payload,
          editing_game_id: editingGameId || null,
        },
      });
      if (error) {
        onShowError("Error al guardar draft", parseApiError(error));
        return;
      }
      // Use data.game_id as needed...

      // Close the draft panel and open the new game
      onClose();
      onChainUpdate();

      // Find and open the latest game
      const chainResult = await apiChain();
      const gameId = findLatestGameId(chainResult.data?.roots ?? []);
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
      let playerA: GameDraftPlayer | null = null;
      let playerB: GameDraftPlayer | null = null;

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
      // 1. Swap country object so that slot retains its assigned properties
      const tempCountry = playerA.country;

      playerA.country = playerB.country;
      playerB.country = tempCountry;

      // 2. Swap the player objects in the state arrays
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
      <p class="loading-text">Generando draft...</p>
    {:else if draftData}
      <PanelSection>
        <SectionTitle title={`Draft de Partidas - Snapshot #${snapshotId}`} />
        <MetaGrid>
          <MetaItem label="Mesas generadas" value={draftData.mesas.length} />
          <MetaItem
            label="Jugadores en espera"
            value={draftData.tickets_sobrantes.length}
          />
          <MetaItem label="Intentos usados" value={draftData.intentos_usados} />
        </MetaGrid>
      </PanelSection>
      {#if draftData.mesas.length > 0}
        <PanelSection>
          <SectionTitle title="Partidas" count={draftData.mesas.length} />
          <CardGrid>
            {#each draftData.mesas as table, tableIndex (table.numero + "_" + tableIndex)}
              <CardGridItem>
                <GameTableCard
                  tableNumber={table.numero}
                  gmName={table.gm ? table.gm.nombre : null}
                >
                  <ul class="player-list">
                    {#each table.jugadores as j, i (j.nombre + "_" + tableIndex + "_" + i)}
                      {@const target = {
                        type: "table" as const,
                        tableIndex,
                        playerIndex: i,
                      }}
                      {@const isSelected = isSelectedSwap(target)}
                      <li class:swapping-active={isSelected}>
                        <span class="p-num">{i + 1}.</span>

                        <PlayerName
                          player={j}
                          compact={true}
                          showNotionIndicator={false}
                        />

                        <select
                          class="country-select"
                          value={j.country?.name || ""}
                          onchange={(e) => {
                            const target = e.target as HTMLSelectElement;
                            handleCountryChange(tableIndex, i, target.value);
                          }}
                        >
                          <option value="">🎲 Aleatorio</option>
                          {#each COUNTRY_OPTIONS as country (country.value)}
                            <option value={country.value}
                              >{country.label}</option
                            >
                          {/each}
                        </select>

                        <div class="tooltip-cell">
                          {#if j.country?.reason}
                            <Tooltip text={j.country.reason} icon="ℹ️" />
                          {/if}
                        </div>

                        <div class="tag-wrapper">
                          <Badge
                            variant={j.is_new ? "warning" : "success"}
                            text={j.is_new ? "Nuevo" : "Antiguo"}
                            fixedWidth={true}
                          />
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
              </CardGridItem>
            {/each}
          </CardGrid>
        </PanelSection>
      {/if}
      {#if draftData.tickets_sobrantes.length > 0}
        <PanelSection>
          <SectionTitle title="Lista de espera" class="waiting-title" />

          <Waitlist
            players={draftData.tickets_sobrantes}
            isSwapping={(i) =>
              isSelectedSwap({ type: "waiting", playerIndex: i })}
          >
            {#snippet actions(i)}
              {@const target = { type: "waiting" as const, playerIndex: i }}
              <Button
                variant="ghost"
                size="sm"
                iconOnly={true}
                icon="🔄"
                title="Intercambiar"
                onclick={() => handlePlayerClick(target)}
              />
            {/snippet}
          </Waitlist>
        </PanelSection>
      {/if}
    {:else}
      <p class="error-text">No se pudo generar el draft</p>
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
  :global(.waiting-title) {
    margin-top: var(--space-16);
  }

  .loading-text {
    color: var(--text-muted);
    font-size: 12px;
    padding: var(--space-4) 0;
  }

  .error-text {
    color: var(--danger-text);
    font-size: 12px;
    padding: var(--space-4) 0;
  }

  .player-list {
    list-style: none;
  }

  .player-list li {
    font-size: 12px;
    padding: var(--space-4) 0;
    display: grid;
    /* Col 1: Num (24px)
      Col 2: Name (minmax forces truncation without blowing out grid)
      Col 3: Dropdown (120px)
      Col 4: Tooltip (24px fixed so dropdowns NEVER shift)
      Col 5: Badge (80px)
      Col 6: Button (32px)
    */
    grid-template-columns:
      var(--space-24) minmax(0, 1fr) 120px var(--space-24)
      80px var(--space-32);
    align-items: center;
    gap: var(--space-8);
    border-bottom: 1px solid var(--border-subtle);
    width: 100%;
  }

  .tooltip-cell {
    display: flex;
    justify-content: center;
    align-items: center;
    width: 100%;
    height: 100%;
  }

  /* Make sure select fills its grid cell perfectly */
  .country-select {
    width: 100%;
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
    justify-content: center;
  }

  .country-select {
    font-size: 11px;
    padding: var(--space-4);
    border: 1px solid var(--border-subtle);
    border-radius: var(--space-4);
    background: var(--bg-primary);
    color: var(--text-primary);
    cursor: pointer;
    width: 100%;
    min-width: 0;
  }

  .swapping-active {
    background: var(--info-bg-subtle);
    outline: 1px solid var(--border-focus);
    border-radius: var(--space-4);
  }
</style>
