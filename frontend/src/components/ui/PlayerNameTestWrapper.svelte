<script lang="ts">
  import PlayerName from "./PlayerName.svelte";
  import type { PlayerData } from "../../types";

  interface Props {
    player: PlayerData;
    editable?: boolean;
    showNotionIndicator?: boolean;
  }

  let {
    player,
    editable = false,
    showNotionIndicator = true,
  }: Props = $props();
</script>

<PlayerName {player} {editable} {showNotionIndicator} />
