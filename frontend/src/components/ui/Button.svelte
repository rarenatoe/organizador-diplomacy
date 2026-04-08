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

  let finalClass = $derived(
    [
      "btn",
      variantClasses[variant],
      size === "sm" ? "btn-sm" : size === "xs" ? "btn-xs" : "",
      fill ? "flex-fill" : "",
      iconOnly ? "btn-icon-only" : "",
      destructive ? "btn-destructive" : "",
      className,
    ]
      .filter(Boolean)
      .join(" "),
  );

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
    gap: 8px;
    padding: 10px 14px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    border: 1px solid transparent;
    transition: all var(--transition-fast);
    font-family: inherit;
    box-shadow: none;
    outline: none;
    box-sizing: border-box;
    line-height: 1;
  }
  .btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
  .btn:focus-visible {
    outline: 2px solid var(--border-focus);
    outline-offset: 2px;
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

  /* Force emojis/icons to be pure white inside solid buttons */
  .btn-primary .btn-icon,
  .btn-success .btn-icon,
  .btn-destructive.btn-primary .btn-icon {
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
    padding: 4px 8px;
    font-size: 11px;
    gap: 4px;
  }

  /* Extra Small Size */
  .btn-xs {
    padding: 2px 4px;
    font-size: 11px;
    gap: 4px;
  }

  /* Icon Only */
  .btn-icon-only {
    padding: 0;
    width: 32px;
    height: 32px;
    flex-shrink: 0;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .btn-sm.btn-icon-only {
    width: 24px;
    height: 24px;
    border-radius: 4px;
  }

  .btn-xs.btn-icon-only {
    width: 20px;
    height: 20px;
    border-radius: 4px;
  }
</style>
