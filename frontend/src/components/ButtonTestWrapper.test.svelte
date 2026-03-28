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
  import Button from './Button.svelte';

  interface Props {
    variant?: 'success' | 'secondary' | 'primary' | 'warning' | 'ghost';
    fill?: boolean;
    disabled?: boolean;
    icon?: string;
    class?: string;
    style?: string;
    title?: string;
    text: string;
    noHandler?: boolean;
  }

  let {
    variant,
    fill,
    disabled,
    icon,
    class: className,
    style,
    title,
    text,
    noHandler = false
  }: Props = $props();

  function handleClick() {
    globalClickCount++;
  }
</script>

<Button
  {...(variant !== undefined && { variant })}
  {...(fill !== undefined && { fill })}
  {...(disabled !== undefined && { disabled })}
  {...(icon !== undefined && { icon })}
  {...(className !== undefined && { class: className })}
  {...(style !== undefined && { style })}
  {...(title !== undefined && { title })}
  {...(!noHandler && { onclick: handleClick })}
>{text}</Button>
