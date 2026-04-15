<script lang="ts">
  import type { Snippet } from "svelte";

  let {
    text,
    icon = "i",
    children,
  }: { text: string; icon?: string; children?: Snippet } = $props();
  let triggerEl = $state<HTMLElement>();
  let isVisible = $state(false);

  function portal(node: HTMLElement) {
    document.body.appendChild(node);
    updatePosition(node);

    const handleUpdate = () => updatePosition(node);
    window.addEventListener("scroll", handleUpdate);
    window.addEventListener("resize", handleUpdate);

    return {
      destroy() {
        window.removeEventListener("scroll", handleUpdate);
        window.removeEventListener("resize", handleUpdate);
        if (node.parentNode) node.parentNode.removeChild(node);
      },
    };
  }

  function updatePosition(popover: HTMLElement) {
    if (!triggerEl) return;
    const rect = triggerEl.getBoundingClientRect();
    popover.style.position = "fixed";
    popover.style.top = `${rect.top - popover.offsetHeight - 8}px`;
    popover.style.left = `${rect.left + rect.width / 2 - popover.offsetWidth / 2}px`;
  }
</script>

<div
  class="tooltip-trigger"
  bind:this={triggerEl}
  onmouseenter={() => (isVisible = true)}
  onmouseleave={() => (isVisible = false)}
  role="tooltip"
>
  {#if children}
    {@render children()}
  {:else}
    <span class="info-icon">{icon}</span>
  {/if}
</div>

{#if isVisible}
  <div use:portal class="tooltip-popover">{text}</div>
{/if}

<style>
  .tooltip-trigger {
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
  .tooltip-trigger:hover .info-icon {
    opacity: 1;
  }
  .tooltip-popover {
    position: fixed;
    background: var(--tooltip-bg);
    color: var(--tooltip-text);
    padding: var(--space-4) var(--space-8);
    border-radius: var(--space-8);
    font-size: 11px;
    font-weight: 500;
    white-space: normal;
    width: max-content;
    max-width: calc(var(--space-8) * 27);
    z-index: 10000;
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
</style>
