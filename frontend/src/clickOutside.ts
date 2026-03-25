interface ClickOutsideParams {
  ignoreSelectors?: string[];
  callback: () => void;
}

export function clickOutside(node: HTMLElement, params: ClickOutsideParams) {
  const handleClick = (event: MouseEvent) => {
    const target = event.target;
    if (!target || !(target instanceof HTMLElement)) return;

    // If the click is inside the panel, do nothing
    if (node.contains(target)) return;

    // If the click is on an element we want to ignore, do nothing
    if (params.ignoreSelectors?.some((selector) => target.closest(selector)))
      return;

    // Otherwise, trigger the callback
    params.callback();
  };

  // Use capture phase to catch the event early
  document.addEventListener("click", handleClick, true);

  return {
    update(newParams: ClickOutsideParams) {
      params = newParams;
    },
    destroy() {
      document.removeEventListener("click", handleClick, true);
    },
  };
}
