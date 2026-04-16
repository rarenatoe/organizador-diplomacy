<script lang="ts">
  import { getActiveNodeId } from "../../stores.svelte";
  import Button from "./Button.svelte";

  interface Props {
    variant: "game" | "snapshot";
    nodeId?: number;
    isActive?: boolean;
    title: string;
    subtitle?: string;
    icon: string;
    metadata: string[];
    onDelete?: () => void;
    onClick: () => void;
  }

  let {
    variant,
    nodeId,
    isActive = false,
    title,
    subtitle = "",
    icon,
    metadata,
    onDelete,
    onClick,
  }: Props = $props();

  // Generate variant-specific classes
  let variantClass = $derived(
    variant === "game" ? "node-game" : "node-snapshot",
  );

  // Parse metadata items intelligently
  function parseMetadataItem(item: string) {
    const text = item.toLowerCase();
    if (/^\d{1,2}:\d{2}:\d{2}$/.test(text)) return { icon: "🕒", text: item };
    if (text.includes("jugadores")) return { icon: "👥", text: item };
    if (text.includes("partida")) return { icon: "🎮", text: item };
    if (text.includes("espera")) return { icon: "⏳", text: item };
    if (text.includes("manual")) return { icon: "✍️", text: "Manual" };
    if (text.includes("notion")) return { icon: "☁️", text: "Notion Sync" };
    if (text.includes("organizar")) return { icon: "⚡", text: "Generado" };
    return { icon: "📌", text: item };
  }
</script>

<div
  class="node group node-{variant}"
  class:active={isActive}
  role="button"
  tabindex="0"
  onclick={onClick}
  onkeydown={(e) => e.key === "Enter" && onClick?.()}
>
  <div class="node-body">
    {#if onDelete}
      <Button
        variant="ghost"
        destructive={true}
        size="xs"
        iconOnly={true}
        icon="🗑"
        class="absolute-top-right group-hover-reveal"
        title={variant === "game" ? "Eliminar jornada" : "Eliminar snapshot"}
        onclick={(e) => {
          e.stopPropagation();
          onDelete();
        }}
      />
    {/if}

    <div class="node-icon">{icon}</div>
    <div class="node-label">{title}</div>
    {#if subtitle}
      <div class="node-name">{subtitle}</div>
    {/if}
  </div>

  <div class="node-footer">
    {#each metadata as item (item)}
      {@const parsed = parseMetadataItem(item)}
      <div class="footer-item">
        <span class="footer-icon">{parsed.icon}</span>
        <span class="footer-text">{parsed.text}</span>
      </div>
    {/each}
  </div>
</div>

<style>
  .node {
    cursor: pointer;
    border-radius: var(--space-12);
    width: calc(var(--space-8) * 22);
    min-height: calc(var(--space-8) * 23);
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
    box-shadow: var(--shadow-base);
    transition:
      transform 0.15s,
      box-shadow 0.15s,
      border-color 0.15s;
    border: 2px solid transparent;
    user-select: none;
    position: relative;
    overflow: hidden;
  }

  .node:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-lg);
  }

  .node.active {
    z-index: 45;
    /* Box-shadow removed from here and moved to the variants below */
  }

  /* --- GAME NODE --- */
  .node-game {
    background: var(--bg-secondary);
    border-color: var(--border-subtle);
    border-left-color: var(--success-border-subtle);
  }

  .node-game.active {
    background: var(--success-bg-active);
    border-color: var(--success-border-subtle);
    border-left-color: var(--success-border);
    box-shadow: 0 0 var(--space-16) 0 var(--success-border-subtle);
  }

  /* --- SNAPSHOT NODE --- */
  .node-snapshot {
    background: var(--bg-secondary);
    border-color: var(--border-subtle);
    border-left-color: var(--info-border-subtle);
  }

  .node-snapshot.active {
    background: var(--info-bg-active);
    border-color: var(--info-border-subtle);
    border-left-color: var(--info-border);
    box-shadow: 0 0 var(--space-16) 0 var(--info-border-subtle);
  }

  /* Node children styling */
  .node-icon {
    font-size: var(--space-16);
    margin-bottom: var(--space-4);
  }

  .node-label {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-muted);
    margin-bottom: var(--space-4);
  }

  .node-body {
    padding: var(--space-16);
    flex: 1;
    display: flex;
    flex-direction: column;
  }

  .node-name {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-primary);
    word-break: break-all;
    line-height: 1.4;
  }

  .node-footer {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
    margin-top: auto;
    background: var(--bg-tertiary);
    padding: var(--space-12) var(--space-16);
    border-top: 1px solid var(--border-subtle);
  }

  .footer-item {
    display: flex;
    align-items: center;
    gap: var(--space-4);
    font-size: 11px;
    color: var(--text-muted);
    line-height: var(--line-height-24);
    font-weight: 500;
  }

  .footer-icon {
    font-size: 10px;
    opacity: 0.7;
    flex-shrink: 0;
  }

  .footer-text {
    flex: 1;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .footer-badge {
    font-size: 9px;
    padding: 1px var(--space-4);
    border-radius: 2px;
    background: var(--bg-secondary);
    color: var(--text-muted);
    border: 1px solid var(--border-subtle);
    text-transform: uppercase;
    letter-spacing: 0.3px;
    font-weight: 600;
  }
</style>
