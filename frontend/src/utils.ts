/**
 * Shared utility functions for the frontend.
 */

/**
 * Escapes HTML special characters to prevent XSS.
 * Uses the browser's built-in HTML escaping via textContent.
 */
export function esc(s: string | null | undefined): string {
  const el = document.createElement("span");
  el.textContent = s ?? "";
  return el.innerHTML;
}
