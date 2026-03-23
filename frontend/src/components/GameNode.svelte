<script lang="ts">
  import type { GameEdge } from "../types";

  interface Props {
    node: GameEdge;
  }

  let { node }: Props = $props();

  let date = $derived((node.created_at || "").split(" ")[0] ?? "");
  let time = $derived((node.created_at || "").split(" ")[1] ?? "");
</script>

<div class="node node-report" data-id={node.id} data-type="game">
  <div class="node-icon">📊</div>
  <div class="node-label">Jornada</div>
  <div class="node-name">{date}</div>
  <div class="node-meta">{time}<br />{node.mesa_count} partida(s)<br />{node.espera_count} en espera</div>
</div>