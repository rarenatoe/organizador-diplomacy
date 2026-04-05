<script lang="ts">
  let { text }: { text: string } = $props();
</script>

<div class="tooltip">
  <span class="info-icon">ℹ️</span>
  <div class="tooltip-popover">{text}</div>
</div>

<style>
  .tooltip {
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
  .tooltip-popover::after {
    content: "";
    position: absolute;
    top: 100%;
    left: 50%;
    margin-left: -4px;
    border-width: 4px;
    border-style: solid;
    border-color: var(--tooltip-bg) transparent transparent transparent;
  }
  .tooltip:hover .tooltip-popover {
    display: block;
  }
</style>
