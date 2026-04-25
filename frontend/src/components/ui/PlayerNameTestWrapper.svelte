<script lang="ts">
  import PlayerName from "./PlayerName.svelte";
  import type { GameDraftPlayer } from "../../generated-api";

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
