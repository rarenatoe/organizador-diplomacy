<script lang="ts">
  let { text, icon = "\u2139\uFE0F" }: { text: string; icon?: string } =
    $props();
</script>

<div class="tooltip">
  <span class="info-icon">{icon}</span>
  <div class="tooltip-popover">{text}</div>
</div>

<style>
  .tooltip {
    position: relative;
    display: inline-flex;
    align-items: center;
    cursor: help;
    margin-left: var(--space-4);
  }
  .info-icon {
    font-size: 11px;
    opacity: 0.7;
    transition: opacity 0.15s;
  }
  .tooltip:hover .info-icon {
    opacity: 1;
  }
  .tooltip-popover {
    display: none;
    position: absolute;
    bottom: 100%;
    left: 50%;
    transform: translateX(-50%);
    background: var(--tooltip-bg);
    color: var(--tooltip-text);
    padding: var(--space-4) var(--space-8);
    border-radius: var(--space-8);
    font-size: 11px;
    font-weight: 500;
    white-space: normal;
    width: max-content;
    max-width: calc(var(--space-8) * 27);
    z-index: 9999;
    margin-bottom: var(--space-8);
    box-shadow: var(--shadow-md);
    text-align: center;
    line-height: var(--line-height-16);
  }
  .tooltip-popover::after {
    content: "";
    position: absolute;
    top: 100%;
    left: 50%;
    margin-left: calc(-1 * var(--space-4));
    border-width: var(--space-4);
    border-style: solid;
    border-color: var(--tooltip-bg) transparent transparent transparent;
  }
  .tooltip:hover .tooltip-popover {
    display: block;
  }
</style>
