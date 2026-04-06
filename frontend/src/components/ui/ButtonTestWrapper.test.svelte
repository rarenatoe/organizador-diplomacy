<script lang="ts" module>
  // Global state store for testing
  let globalClickCount = 0;
  export function resetClickCount() {
    globalClickCount = 0;
  }
  export function getClickCount() {
    return globalClickCount;
  }
</script>

<script lang="ts">
  import Button from "./Button.svelte";

  interface Props {
    variant?: "success" | "secondary" | "primary" | "warning" | "ghost";
    fill?: boolean;
    disabled?: boolean;
    icon?: string;
    size?: "md" | "sm" | "xs";
    class?: string;
    style?: string;
    title?: string;
    text: string;
    noHandler?: boolean;
    destructive?: boolean;
  }

  let {
    variant,
    fill,
    disabled,
    icon,
    size,
    class: className,
    style,
    title,
    text,
    noHandler = false,
    destructive,
  }: Props = $props();

  function handleClick() {
    globalClickCount++;
  }
</script>

<Button
  {...variant !== undefined && { variant }}
  {...fill !== undefined && { fill }}
  {...disabled !== undefined && { disabled }}
  {...icon !== undefined && { icon }}
  {...size !== undefined && { size }}
  {...destructive !== undefined && { destructive }}
  {...className !== undefined && { class: className }}
  {...style !== undefined && { style }}
  {...title !== undefined && { title }}
  {...!noHandler && { onclick: handleClick }}>{text}</Button
>
