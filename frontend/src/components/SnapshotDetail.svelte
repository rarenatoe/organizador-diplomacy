<script lang="ts">
  import type { SnapshotDetail, EditPlayerRow } from "../types";
  import { fetchSnapshot, editSnapshot, addPlayer, renamePlayer } from "../api";
  import { setSelectedSnapshot } from "../stores.svelte";

  interface Props {
    id: number;
    onclose: () => void;
    onchainUpdate: () => void;
    onopenSnapshot: (id: number) => void;
  }

  let { id, onclose, onchainUpdate, onopenSnapshot }: Props = $props();

  let data = $state<SnapshotDetail | null>(null);
  let loading = $state(true);

  const CSV_COLS = [
    "nombre",
    "experiencia",
    "juegos_este_ano",
    "prioridad",
    "partidas_deseadas",
    "partidas_gm",
  ] as const;

  type Col = (typeof CSV_COLS)[number];

  function esc(s: string | null | undefined): string {
    const el = document.createElement("span");
    el.textContent = s ?? "";
    return el.innerHTML;
  }

  function sourceLabel(source: string | undefined): string {
    if (source === "notion_sync") return "☁️ Notion Sync";
    if (source === "organizar") return "▶ Organizar";
    return "📥 Manual";
  }

  async function loadSnapshot(): Promise<void> {
    loading = true;
    try {
      data = await fetchSnapshot(id);
    } finally {
      loading = false;
    }
  }

  function getCsvText(): string {
    if (!data?.players) return "";
    const rows = data.players;
    return [
      CSV_COLS.join(","),
      ...rows.map((r) =>
        CSV_COLS.map((c: Col) =>
          String((r as Record<Col, string | number>)[c]),
        ).join(","),
      ),
    ].join("\n");
  }

  async function copyCsv(): Promise<void> {
    await navigator.clipboard.writeText(getCsvText());
  }

  async function handleApplyEdit(): Promise<void> {
    const table = document.getElementById("snapshot-edit-table");
    if (!table || !data) return;
    const players: EditPlayerRow[] = [];
    table.querySelectorAll<HTMLTableRowElement>("tbody tr").forEach((tr) => {
      const keep = tr.querySelector<HTMLInputElement>(".player-keep");
      if (!keep?.checked) return;
      const nombre = tr.dataset["nombre"] ?? "";
      const prio = tr.querySelector<HTMLInputElement>(".player-prio");
      const deseadas = tr.querySelector<HTMLInputElement>(".player-deseadas");
      const gm = tr.querySelector<HTMLInputElement>(".player-gm");
      players.push({
        nombre,
        prioridad: prio?.checked ? 1 : 0,
        partidas_deseadas: parseInt(deseadas?.value ?? "1", 10),
        partidas_gm: gm?.checked ? 1 : 0,
      });
    });
    const result = await editSnapshot(id, players);
    if (result.error) {
      alert(`Error: ${result.error}`);
      return;
    }
    onclose();
    onchainUpdate();
    if (result.snapshot_id !== undefined) {
      setSelectedSnapshot(result.snapshot_id);
      onopenSnapshot(result.snapshot_id);
    }
  }

  async function handleRename(oldName: string): Promise<void> {
    const newName = prompt(`Renombrar jugador "${oldName}" a:`, oldName);
    if (!newName || newName === oldName) return;
    const result = await renamePlayer(oldName, newName);
    if (result.error) {
      alert(`Error: ${result.error}`);
      return;
    }
    await loadSnapshot();
    onchainUpdate();
  }

  async function handleAddPlayer(): Promise<void> {
    const nombre = prompt("Nombre del nuevo jugador:");
    if (!nombre) return;
    const experiencia = prompt("Experiencia (Nuevo/Antiguo):", "Nuevo");
    if (!experiencia) return;
    const juegosStr = prompt("Juegos este año:", "0");
    const juegos = parseInt(juegosStr ?? "0", 10);
    const result = await addPlayer(id, {
      nombre,
      experiencia,
      juegos_este_ano: juegos,
      prioridad: 0,
      partidas_deseadas: 1,
      partidas_gm: 0,
    });
    if (result.error) {
      alert(`Error: ${result.error}`);
      return;
    }
    await loadSnapshot();
    onchainUpdate();
  }

  function handleCheckboxChange(e: Event): void {
    const cb = (e.target as Element).closest<HTMLInputElement>(".player-keep");
    if (!cb) return;
    const tr = cb.closest("tr");
    if (tr) tr.classList.toggle("excluded", !cb.checked);
  }

  $effect(() => {
    void loadSnapshot();
  });
</script>

{#if loading}
  <p style="color:var(--muted);font-size:12px;padding:4px 0">Cargando…</p>
{:else if data}
  {@const rows = data.players ?? []}
  <div class="panel-body-fixed">
    <div class="section" style="margin-bottom: 16px;">
      <div class="section-title">Snapshot #{id} · {sourceLabel(data.source)}</div>
      <div class="node-meta" style="margin-bottom:8px">{esc(data.created_at)}</div>
      <button class="copy-btn" onclick={copyCsv}>📋 Copiar tabla CSV</button>
    </div>
    <div class="section-title" style="margin-bottom:6px">
      Jugadores <span
        style="color:var(--muted);font-weight:400;text-transform:none;font-size:11px"
        >— desactiva para excluir de la siguiente jornada</span
      >
    </div>
  </div>

  <div class="table-wrap flex-table-wrap">
    <table id="snapshot-edit-table">
          <thead>
            <tr>
              <th></th>
              <th>Nombre</th>
              <th></th>
              <th>Exp.</th>
              <th>Juegos</th>
              <th>Prior.</th>
              <th>Desea</th>
              <th>GM</th>
            </tr>
          </thead>
          <tbody onchange={handleCheckboxChange}>
            {#each rows as r}
              {@const nombre = esc(String(r["nombre"] ?? ""))}
              {@const expColor =
                r["experiencia"] === "Nuevo" ? "#713f12" : "#166534"}
              {@const expBg =
                r["experiencia"] === "Nuevo" ? "#fef9c3" : "#f0fdf4"}
              <tr data-nombre={nombre}>
                <td
                  ><input
                    type="checkbox"
                    class="player-keep"
                    checked
                    title="Incluir"
                  /></td
                >
                <td><span class="player-name">{nombre}</span></td>
                <td style="padding-left: 0; width: 32px;">
                  <button
                    class="btn-ghost btn-rename"
                    title="Renombrar"
                    onclick={() => handleRename(String(r["nombre"] ?? ""))}
                    >✏️</button
                  >
                </td>
                <td
                  ><span
                    style="font-size:10px;font-weight:700;color:{expColor};background:{expBg};padding:1px 6px;border-radius:4px"
                    >{esc(String(r["experiencia"] ?? ""))}</span
                  ></td
                >
                <td>{String(r["juegos_este_ano"] ?? "")}</td>
                <td
                  ><input
                    type="checkbox"
                    class="player-prio"
                    checked={r["prioridad"] === 1}
                  /></td
                >
                <td
                  ><input
                    type="number"
                    class="player-deseadas"
                    value={String(r["partidas_deseadas"] ?? "1")}
                    min="1"
                    max="9"
                    style="width:38px"
                  /></td
                >
                <td
                  ><input
                    type="checkbox"
                    class="player-gm"
                    checked={(r["partidas_gm"] as number) > 0}
                  /></td
                >
              </tr>
            {/each}
          </tbody>
        </table>
  </div>
  <div class="panel-footer">
    <button
      class="btn btn-secondary"
      style="width:100%"
      onclick={handleAddPlayer}>➕ Agregar jugador</button
    >
    <button class="btn btn-primary" style="width:100%" onclick={handleApplyEdit}
      >✨ Crear snapshot manual con estos ajustes</button
    >
  </div>
{/if}
