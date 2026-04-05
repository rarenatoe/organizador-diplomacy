<script lang="ts">
  interface Props {
    variant: "info" | "success" | "warning" | "error";
    text: string;
    pill?: boolean;
    fixedWidth?: boolean;
  }

  let { variant, text, pill = false, fixedWidth = false }: Props = $props();
</script>

<span class="badge {variant}" class:pill class:fixed-width={fixedWidth}
  >{text}</span
>

<style>
  .badge {
    font-size: 10px;
    padding: 2px 6px;
    border-radius: 4px;
    font-weight: 600;
    white-space: nowrap;
    text-align: center;
    display: inline-block;
    border: 1px solid transparent;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  }

  .pill {
    border-radius: 99px;
    padding: 2px 8px;
    font-size: 11px;
  }

  /* Explicit alignment class for table layouts */
  .fixed-width {
    min-width: 75px;
  }

  .info {
    background: var(--info-bg);
    color: var(--info-dark);
    border-color: var(--info-border);
  }

  .success {
    background: var(--success-bg);
    color: var(--success-dark);
    border-color: var(--success-border);
  }

  .warning {
    background: var(--warning-bg);
    color: var(--warning-dark);
    border-color: var(--warning-border);
  }

  .error {
    background: var(--error-bg);
    color: var(--error-dark);
    border-color: var(--error-border);
  }
</style>
