<script lang="ts">
  import type { Snippet } from "svelte";

  interface Props {
    variant?: "primary" | "secondary" | "success" | "warning" | "ghost";
    fill?: boolean;
    disabled?: boolean;
    icon?: string;
    size?: "md" | "sm";
    iconOnly?: boolean;
    type?: "button" | "submit" | "reset";
    class?: string;
    style?: string;
    title?: string;
    onclick?: (e: MouseEvent) => void;
    children?: Snippet;
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
      size === "sm" ? "btn-sm" : "",
      fill ? "flex-fill" : "",
      iconOnly ? "btn-icon-only" : "",
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
    transition: all 0.15s ease;
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
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
  .flex-fill {
    flex: 1 1 auto;
    width: 100%;
  }

  /* Primary */
  .btn-primary {
    background: var(--accent);
    color: white;
    border-color: var(--accent);
  }
  .btn-primary:hover:not(:disabled) {
    background: #2563eb;
  }

  /* Secondary */
  .btn-secondary {
    background: var(--surface2);
    border-color: var(--border);
    color: var(--text);
  }
  .btn-secondary:hover:not(:disabled) {
    background: var(--border);
  }

  /* Success */
  .btn-success {
    background: var(--success);
    color: white;
    border-color: var(--success);
  }
  .btn-success:hover:not(:disabled) {
    background: #16a34a;
  }

  /* Warning */
  .btn-warning {
    background: #eab308;
    color: #422006;
    border-color: #eab308;
  }
  .btn-warning:hover:not(:disabled) {
    background: #ca8a04;
  }

  /* Ghost */
  .btn-ghost {
    background: transparent;
    border-color: transparent;
    color: var(--text);
    padding: 4px 8px;
  }
  .btn-ghost:hover:not(:disabled) {
    background: var(--border);
    border-color: transparent;
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
</style>
