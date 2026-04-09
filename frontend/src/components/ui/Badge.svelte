<script lang="ts">
  interface Props {
    variant: "info" | "success" | "warning" | "error";
    text: string;
    pill?: boolean;
    fixedWidth?: boolean;
    subtle?: boolean;
  }

  let {
    variant,
    text,
    pill = false,
    fixedWidth = false,
    subtle = true,
  }: Props = $props();
</script>

<span
  class="badge {variant}"
  class:pill
  class:fixed-width={fixedWidth}
  class:subtle>{text}</span
>

<style>
  .badge {
    font-size: 10px;
    padding: var(--space-4) var(--space-8);
    border-radius: var(--space-4);
    font-weight: 600;
    white-space: nowrap;
    text-align: center;
    display: inline-block;
    border: 1px solid transparent;
    box-shadow: var(--shadow-sm);
  }

  .pill {
    border-radius: var(--space-16);
    padding: var(--space-4) var(--space-8);
    font-size: 11px;
  }

  /* Explicit alignment class for table layouts */
  .fixed-width {
    min-width: var(--space-72);
  }

  /* Info */
  .info.subtle {
    background: var(--info-bg-subtle);
    color: var(--info-text-subtle);
    border-color: var(--info-border-subtle);
  }
  .info:not(.subtle) {
    background: var(--info-bg);
    color: var(--info-text);
    border-color: var(--info-border);
  }

  /* Success */
  .success.subtle {
    background: var(--success-bg-subtle);
    color: var(--success-text-subtle);
    border-color: var(--success-border-subtle);
  }
  .success:not(.subtle) {
    background: var(--success-bg);
    color: var(--success-text);
    border-color: var(--success-border);
  }

  /* Warning */
  .warning.subtle {
    background: var(--warning-bg-subtle);
    color: var(--warning-text-subtle);
    border-color: var(--warning-border-subtle);
  }
  .warning:not(.subtle) {
    background: var(--warning-bg);
    color: var(--warning-text);
    border-color: var(--warning-border);
  }

  /* Error */
  .error.subtle {
    background: var(--danger-bg-subtle);
    color: var(--danger-text-subtle);
    border-color: var(--danger-border-subtle);
  }
  .error:not(.subtle) {
    background: var(--danger-bg);
    color: var(--danger-text);
    border-color: var(--danger-border);
  }
</style>
