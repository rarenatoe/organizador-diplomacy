<script lang="ts">
  import type { GameDetail } from "../types";
  import { fetchGame } from "../api";

  interface Props {
    id: number;
  }

  let { id }: Props = $props();

  let data = $state<GameDetail | null>(null);
  let loading = $state(true);

  function esc(s: string | null | undefined): string {
    const el = document.createElement("span");
    el.textContent = s ?? "";
    return el.innerHTML;
  }

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
{/if}