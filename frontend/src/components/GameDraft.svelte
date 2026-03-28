<script lang="ts">
  import type { DraftResponse, DraftPlayer, DraftMesa } from "../types";
  import { fetchGameDraft, saveGameDraft } from "../api";
  import { setActiveNodeId } from "../stores.svelte";
  import { findLatestGameId } from "../snapshotUtils";

  interface Props {
    snapshotId: number;
    onClose: () => void;
    onChainUpdate: () => void;
    onOpenGame: (id: number) => void;
    onShowError: (title: string, output: string) => void;
    editingGameId?: number | null;
    initialDraft?: DraftResponse | null;
  }

  let { snapshotId, onClose, onChainUpdate, onOpenGame, onShowError, editingGameId, initialDraft }: Props = $props();

  let draftData = $state<DraftResponse | null>(null);
  let loading = $state(true);
  let saving = $state(false);
  
  type SwapTarget = { type: 'mesa', mesaIndex: number, playerIndex: number } | { type: 'espera', playerIndex: number };
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

  function handleCountryChange(mesaIndex: number, playerIndex: number, newCountry: string): void {
    if (!draftData) return;
    
    // Check if the new country is already assigned to another player in the same mesa
    const mesa = draftData.mesas[mesaIndex];
    if (!mesa) return;
    
    const conflictingPlayer = mesa.jugadores.find((j, idx) => 
      idx !== playerIndex && j.pais === newCountry && newCountry !== ""
    );
    
    if (conflictingPlayer) {
      // Automatically swap countries between the two players
      const conflictingPlayerIndex = mesa.jugadores.indexOf(conflictingPlayer);
      const currentPlayer = mesa.jugadores[playerIndex]!;
      const tempCountry = currentPlayer.pais;
      
      // Assign new country to current player
      if (newCountry !== "") {
        currentPlayer.pais = newCountry;
      } else {
        // Handle "Aleatorio" selection - remove country assignment
        currentPlayer.pais = "";
      }
      
      // Give old country to conflicting player
      const conflictingPlayerObj = mesa.jugadores[conflictingPlayerIndex];
      if (conflictingPlayerObj) {
        conflictingPlayerObj.pais = tempCountry;
      }
    } else {
      // Just assign country if no conflict
      const currentPlayer = mesa.jugadores[playerIndex]!;
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
      const cleanMesas = draftData.mesas.map((mesa) => ({
        ...mesa,
        jugadores: mesa.jugadores.map(({ pais, pais_reason, ...rest }) => ({
          ...rest,
          pais: pais || "",
          ...(pais_reason ? { pais_reason } : {}),
        })),
      }));
      const cleanTicketsSobrantes = draftData.tickets_sobrantes.map(({ pais, pais_reason, ...rest }) => ({
        ...rest,
        pais: pais || "",
        ...(pais_reason ? { pais_reason } : {}),
      }));
      const payload: DraftResponse = { ...draftData, mesas: cleanMesas, tickets_sobrantes: cleanTicketsSobrantes };

      const response = await saveGameDraft({ 
        snapshot_id: snapshotId, 
        draft: payload, 
        editing_game_id: editingGameId || null
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
      if (selectedSwap.type === target.type && 
          selectedSwap.type === 'mesa' && 
          target.type === 'mesa' &&
          selectedSwap.mesaIndex === target.mesaIndex && 
          selectedSwap.playerIndex === target.playerIndex) {
        // Clicked the same player - cancel selection
        selectedSwap = null;
        return;
      }
      
      // Get the two players to swap
      let playerA: DraftPlayer | null = null;
      let playerB: DraftPlayer | null = null;
      
      // Extract Player A
      if (selectedSwap.type === 'mesa') {
        const mesaAIndex = selectedSwap.mesaIndex;
        const mesaA = draftData.mesas[mesaAIndex];
        if (mesaA) {
          playerA = mesaA.jugadores[selectedSwap.playerIndex] ?? null;
        }
      } else {
        playerA = draftData.tickets_sobrantes[selectedSwap.playerIndex] ?? null;
      }
      
      // Extract Player B
      if (target.type === 'mesa') {
        const mesaBIndex = target.mesaIndex;
        const mesaB = draftData.mesas[mesaBIndex];
        if (mesaB) {
          playerB = mesaB.jugadores[target.playerIndex] ?? null;
        }
      } else {
        playerB = draftData.tickets_sobrantes[target.playerIndex] ?? null;
      }
      
      if (!playerA || !playerB) {
        onShowError("Error", "No se encontraron los jugadores para intercambiar.");
        selectedSwap = null;
        return;
      }
      
      // Constraint: Check for duplicates in destination tables
      if (target.type === 'mesa') {
        const mesaAIndex = target.mesaIndex;
        const mesaA = draftData.mesas[mesaAIndex];
        if (mesaA) {
          const hasDuplicate = mesaA.jugadores.some(p => p.nombre === playerA.nombre && p !== playerA);
          if (hasDuplicate) {
            onShowError("Movimiento Inválido", `El jugador ${playerA.nombre} ya está en la mesa ${mesaA.numero}.`);
            selectedSwap = null;
            return;
          }
        }
      }
      
      if (selectedSwap.type === 'mesa') {
        const mesaBIndex = selectedSwap.mesaIndex;
        const mesaB = draftData.mesas[mesaBIndex];
        if (mesaB) {
          const hasDuplicate = mesaB.jugadores.some(p => p.nombre === playerB.nombre && p !== playerB);
          if (hasDuplicate) {
            onShowError("Movimiento Inválido", `El jugador ${playerB.nombre} ya está en la mesa ${mesaB.numero}.`);
            selectedSwap = null;
            return;
          }
        }
      }
      
      // Execute the swap
      if (selectedSwap.type === 'mesa') {
        const selectedMesaIndex = selectedSwap.mesaIndex;
        const selectedPlayerIndex = selectedSwap.playerIndex;
        
        if (target.type === 'mesa') {
          // Mesa to Mesa swap
          const targetMesaIndex = target.mesaIndex;
          const targetPlayerIndex = target.playerIndex;
          
          if (draftData.mesas[selectedMesaIndex]?.jugadores[selectedPlayerIndex] && 
              draftData.mesas[targetMesaIndex]?.jugadores[targetPlayerIndex]) {
            // Swap countries so slot retains assigned country
            const tempPais = draftData.mesas[selectedMesaIndex].jugadores[selectedPlayerIndex].pais;
            const targetPais = draftData.mesas[targetMesaIndex].jugadores[targetPlayerIndex].pais;
            
            draftData.mesas[selectedMesaIndex].jugadores[selectedPlayerIndex].pais = targetPais;
            draftData.mesas[targetMesaIndex].jugadores[targetPlayerIndex].pais = tempPais;
            
            draftData.mesas[selectedMesaIndex].jugadores[selectedPlayerIndex] = playerB;
            draftData.mesas[targetMesaIndex].jugadores[targetPlayerIndex] = playerA;
          }
        } else {
          // Mesa to Espera swap
          const targetPlayerIndex = target.playerIndex;
          
          if (draftData.mesas[selectedMesaIndex]?.jugadores[selectedPlayerIndex] && 
              draftData.tickets_sobrantes[targetPlayerIndex] !== undefined) {
            // Swap countries so slot retains assigned country
            const tempPais = draftData.mesas[selectedMesaIndex].jugadores[selectedPlayerIndex].pais;
            const targetPais = draftData.tickets_sobrantes[targetPlayerIndex].pais;
            
            draftData.mesas[selectedMesaIndex].jugadores[selectedPlayerIndex].pais = targetPais;
            draftData.tickets_sobrantes[targetPlayerIndex].pais = tempPais;
            
            draftData.mesas[selectedMesaIndex].jugadores[selectedPlayerIndex] = playerB;
            draftData.tickets_sobrantes[targetPlayerIndex] = playerA;
          }
        }
      } else {
        const selectedPlayerIndex = selectedSwap.playerIndex;
        
        if (target.type === 'mesa') {
          // Espera to Mesa swap
          const targetMesaIndex = target.mesaIndex;
          const targetPlayerIndex = target.playerIndex;
          
          if (draftData.tickets_sobrantes[selectedPlayerIndex] !== undefined && 
              draftData.mesas[targetMesaIndex]?.jugadores[targetPlayerIndex]) {
            // Swap countries so slot retains assigned country
            const tempPais = draftData.tickets_sobrantes[selectedPlayerIndex].pais;
            const targetPais = draftData.mesas[targetMesaIndex].jugadores[targetPlayerIndex].pais;
            
            draftData.tickets_sobrantes[selectedPlayerIndex].pais = targetPais;
            draftData.mesas[targetMesaIndex].jugadores[targetPlayerIndex].pais = tempPais;
            
            draftData.tickets_sobrantes[selectedPlayerIndex] = playerB;
            draftData.mesas[targetMesaIndex].jugadores[targetPlayerIndex] = playerA;
          }
        } else {
          // Espera to Espera swap
          const targetPlayerIndex = target.playerIndex;
          
          if (draftData.tickets_sobrantes[selectedPlayerIndex] !== undefined && 
              draftData.tickets_sobrantes[targetPlayerIndex] !== undefined) {
            // Swap countries so slot retains assigned country
            const tempPais = draftData.tickets_sobrantes[selectedPlayerIndex].pais;
            const targetPais = draftData.tickets_sobrantes[targetPlayerIndex].pais;
            
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
    
    if (selectedSwap.type === 'mesa' && target.type === 'mesa') {
      return selectedSwap.mesaIndex === target.mesaIndex && selectedSwap.playerIndex === target.playerIndex;
    } else if (selectedSwap.type === 'espera' && target.type === 'espera') {
      return selectedSwap.playerIndex === target.playerIndex;
    }
    return false;
  }

  loadDraft();
</script>

<div class="panel-scroll">
  {#if loading}
    <p style="color:var(--muted);font-size:12px;padding:4px 0">Generando draft...</p>
  {:else if draftData}
    <div class="section">
      <div class="section-title">Draft de Partidas - Snapshot #{snapshotId}</div>
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
        {#each draftData.mesas as mesa, mesaIndex (mesa.numero)}
          <div class="mesa-card">
            <div class="mesa-header">
              <span class="mesa-title">Partida {mesa.numero}</span>
              {#if mesa.gm}
                <span class="gm-tag gm-tag-ok">GM: {mesa.gm.nombre}</span>
              {:else}
                <span class="gm-tag gm-tag-bad">⚠️ Sin GM</span>
              {/if}
            </div>
            <ul class="player-list">
              {#each mesa.jugadores as j, i (j.nombre)}
                {@const target = { type: 'mesa' as const, mesaIndex, playerIndex: i } }
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
                      handleCountryChange(mesaIndex, i, target.value);
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
                      <div class="reason-tooltip">
                        <span class="info-icon">ℹ️</span>
                        <div class="tooltip-popover">{j.pais_reason}</div>
                      </div>
                    {/if}
                  </div>
                  {#if j.es_nuevo}
                    <span class="tag tag-nuevo">Nuevo</span>
                  {:else}
                    <span class="tag tag-antiguo">Antiguo</span>
                  {/if}
                  <button 
                    class="btn-ghost btn-swap" 
                    title="Intercambiar"
                    onclick={() => handlePlayerClick(target)}
                  >🔄</button>
                </li>
              {/each}
            </ul>
          </div>
        {/each}
      </div>
    {/if}
    {#if draftData.tickets_sobrantes.length > 0}
      <div class="section">
        <div class="section-title">Lista de espera</div>
        {#each draftData.tickets_sobrantes as w, i (w.nombre)}
          {@const target = { type: 'espera' as const, playerIndex: i } }
          {@const isSelected = isSelectedSwap(target)}
          <div class="waiting-item" class:swapping-active={isSelected}>
            <span class="waiting-name">{w.nombre}</span>
            <span class="waiting-cupos">{w.partidas_deseadas} cupos</span>
            <button 
              class="btn-ghost btn-swap" 
              title="Intercambiar"
              onclick={() => handlePlayerClick(target)}
            >🔄</button>
          </div>
        {/each}
      </div>
    {/if}
  {:else}
    <p style="color:var(--danger);font-size:12px;padding:4px 0">No se pudo generar el draft</p>
  {/if}
</div>
<div class="panel-footer">
  {#if draftData}
    <button 
      class="btn btn-secondary" 
      style="width:100%"
      onclick={() => {
        if (editingGameId) {
          onOpenGame(editingGameId);
        } else {
          onClose();
        }
      }}
      disabled={saving}
    >
      Cancelar
    </button>
    <button 
      class="btn btn-primary" 
      style="width:100%"
      onclick={handleSaveDraft}
      disabled={saving}
    >
      {saving ? "⏳ Guardando..." : "✨ Confirmar y Guardar"}
    </button>
  {/if}
</div>

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
    content: '';
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

  .btn-swap {
    font-size: 12px;
    padding: 2px 6px;
    opacity: 0.7;
    transition: opacity 0.15s;
  }

  .btn-swap:hover {
    opacity: 1;
  }

  .swapping-active {
    background: #eff6ff;
    outline: 1px solid var(--accent);
    border-radius: 4px;
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

  .waiting-item.swapping-active {
    background: #eff6ff;
    outline: 1px solid var(--accent);
    border-color: var(--accent);
  }

  .waiting-name {
    font-weight: 600;
  }

  .waiting-cupos {
    color: #92400e;
    font-size: 11px;
  }
</style>
