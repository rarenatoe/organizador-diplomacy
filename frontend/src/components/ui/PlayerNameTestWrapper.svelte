<script lang="ts">
  import type { GameDraftPlayer } from "../../generated-api";
  import PlayerName from "./PlayerName.svelte";

  interface Props {
    player: GameDraftPlayer;
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
