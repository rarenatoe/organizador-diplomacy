<script lang="ts">
  import type { Snippet } from "svelte";

  interface Props {
    variant?: "primary" | "secondary" | "success" | "warning" | "ghost";
    fill?: boolean;
    disabled?: boolean;
    icon?: string;
    size?: "md" | "sm" | "xs";
    iconOnly?: boolean;
    type?: "button" | "submit" | "reset";
    class?: string;
    style?: string;
    title?: string;
    onclick?: (e: MouseEvent) => void;
    children?: Snippet;
    destructive?: boolean;
  }

  let {
    variant = "secondary",
    fill = false,
    disabled = false,
    icon = "",
    size = "md",
    iconOnly = false,
    type = "button",
    class: className = "",
    style = "",
    title = "",
    onclick,
    children,
    destructive = false,
  }: Props = $props();

  const variantClasses: Record<string, string> = {
    primary: "btn-primary",
    secondary: "btn-secondary",
    success: "btn-success",
    warning: "btn-warning",
    ghost: "btn-ghost",
  };

  let finalClass = $derived.by(() => {
    const sizeClassMap = {
      sm: "btn-sm",
      md: "btn",
      xs: "btn-xs",
    } as const;
    let sizeClass = sizeClassMap[size];

    return [
      "btn",
      variantClasses[variant],
      sizeClass,
      fill ? "flex-fill" : "",
      iconOnly ? "btn-icon-only" : "",
      destructive ? "btn-destructive" : "",
      className,
    ]
      .filter(Boolean)
      .join(" ");
  });

  function handleClick(e: MouseEvent) {
    if (!disabled && onclick) {
      onclick(e);
    }
  }
</script>

<button
  {type}
  class={finalClass}
  {style}
  {title}
  {disabled}
  onclick={handleClick}
>
  {#if icon}<span class="btn-icon">{icon}</span>{/if}
  {#if children}<span>{@render children()}</span>{/if}
</button>

<style>
  .btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-8);
    padding: var(--space-8) var(--space-16);
    border-radius: var(--space-8);
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    border: 1px solid transparent;
    transition: all var(--transition-fast);
    font-family: inherit;
    box-shadow: none;
    outline: none;
    box-sizing: border-box;
    line-height: var(--line-height-16);
  }
  .btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
  .btn:focus-visible {
    outline: 2px solid var(--border-focus);
    outline-offset: var(--space-4);
  }
  .flex-fill {
    flex: 1 1 auto;
    width: 100%;
  }

  /* --- SOLID BUTTON BASE --- */
  /* All solid intent buttons share a baseline shadow for elevation */
  .btn-primary,
  .btn-success,
  .btn-warning,
  .btn-destructive.btn-primary {
    box-shadow: var(--shadow-sm);
  }

  /* Primary */
  .btn-primary {
    background: var(--primary-bg);
    color: var(--primary-text);
    border-color: var(--primary-border);
  }
  .btn-primary:hover:not(:disabled) {
    background: var(--primary-hover);
    border-color: var(--primary-hover);
  }

  /* Success */
  .btn-success {
    background: var(--success-bg);
    color: var(--success-text);
    border-color: var(--success-border);
  }
  .btn-success:hover:not(:disabled) {
    background: var(--success-hover);
    border-color: var(--success-hover);
  }

  /* Warning */
  .btn-warning {
    background: var(--warning-bg);
    color: var(--warning-text);
    border-color: var(--warning-border);
  }
  .btn-warning:hover:not(:disabled) {
    background: var(--warning-hover);
    border-color: var(--warning-hover);
  }

  /* --- SECONDARY BUTTON --- */
  .btn-secondary {
    background: var(--bg-secondary);
    border-color: var(--border-default);
    color: var(--text-secondary);
    box-shadow: var(--shadow-sm);
  }
  .btn-secondary:hover:not(:disabled) {
    background: var(--bg-tertiary);
    color: var(--text-primary);
    border-color: var(--border-default);
  }

  /* --- GHOST BUTTON --- */
  .btn-ghost {
    background: transparent;
    border-color: transparent;
    color: var(--text-secondary);
  }
  .btn-ghost:hover:not(:disabled) {
    background: var(--overlay-hover);
    color: var(--text-primary);
    border-color: transparent;
  }

  /* --- DESTRUCTIVE MODIFIERS --- */
  .btn-destructive.btn-ghost {
    color: var(--red-600);
  }
  .btn-destructive.btn-ghost:hover:not(:disabled) {
    background: var(
      --overlay-destructive
    ); /* 12% Red creates a vivid tint on any background */
    color: var(--red-700);
  }

  .btn-destructive.btn-primary {
    background: var(--danger-bg);
    border-color: var(--danger-border);
    color: var(--danger-text);
  }
  .btn-destructive.btn-primary:hover:not(:disabled) {
    background: var(--danger-hover);
    border-color: var(--danger-hover);
  }

  /* Force external images and SVGs to be pure white inside solid buttons */
  /* We specifically target img and svg, avoiding text-based emojis so they don't turn into white squares */
  .btn-primary .btn-icon :global(img),
  .btn-primary .btn-icon :global(svg),
  .btn-success .btn-icon :global(img),
  .btn-success .btn-icon :global(svg),
  .btn-destructive.btn-primary .btn-icon :global(img),
  .btn-destructive.btn-primary .btn-icon :global(svg) {
    filter: brightness(0) invert(1);
  }

  /* Icon */
  .btn-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    line-height: 1;
  }

  /* Sizes */
  .btn-sm {
    padding: var(--space-4) var(--space-8);
    font-size: 11px;
    gap: var(--space-4);
  }

  /* Extra Small Size */
  .btn-xs {
    padding: var(--space-4) var(--space-4);
    font-size: 11px;
    gap: var(--space-4);
  }

  /* Icon Only */
  .btn-icon-only {
    padding: 0;
    width: var(--space-32);
    height: var(--space-32);
    flex-shrink: 0;
    border-radius: var(--space-8);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .btn-sm.btn-icon-only {
    width: var(--space-24);
    height: var(--space-24);
    border-radius: var(--space-4);
  }

  .btn-xs.btn-icon-only {
    width: var(--space-16);
    height: var(--space-16);
    border-radius: var(--space-4);
  }
</style>
