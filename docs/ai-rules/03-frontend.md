---
id: frontend
title: Pillar 3 - Frontend & Svelte 5 Conventions
priority: 30
---

## 1. Core Architecture & Organization

- **Tech Stack:** Svelte 5, TypeScript, Vite. Do not use alternative frameworks.
- **File Limits:** Maintain a 400-line soft limit per file. Extract sub-domains/components when exceeded.
- **Localization:** Route ALL UI translations through `frontend/src/i18n.ts`. No hardcoded strings.
- **Component Routing:** Categorize `frontend/src/components/` strictly by responsibility:
  - `ui/`: Atomic, domain-agnostic elements (Buttons, Badges).
  - `modals/`: Overlays and dialogs.
  - `layout/`: Structural containers.
  - `features/`: Domain-specific logic and complex views.
- **Logging:** Use `logger.info()`, `warn()`, and `error()` from `src/utils/logger.ts`. NEVER use `console.log()`.

## 2. Svelte 5 Reactivity & State

- **Runes:** Use `$state`, `$derived`, and `$effect`. Never use `let` for reactive variables.
- **Complex Derivations:** NEVER use nested ternary operators. For complex conditionals, use `$derived.by(() => { if (x) return y; return z; })`.
- **Context-Aware Components:** Prefer using `$derived` state (e.g., `isEditing = $derived(parentId !== null)`) to adapt a single component for Create/Edit views instead of duplicating the entire component file.
- **Global State:** Store global state in `stores.svelte.ts`. Use standard loading states: `-1` (unknown/loading) and `0` (loaded).

## 3. Component API Design

- **Separation of Concerns:** Keep Visual props (`variant`, `size`) strictly separate from Layout props (`fixedWidth`, `align`).
- **Domain-Agnostic Leaf Nodes:** Components in `ui/` MUST use semantic props (e.g., `variant="info"`). Never use domain terminology (e.g., `variant="gm"`).
- **Domain-Specific Nodes:** Components in `features/` MUST accept domain data explicitly (e.g., `gmName`, `players`).
- **Snippets over HTML:** Type snippets using `import type { Snippet } from "svelte"`. When passing dynamic rows to structural components (like `<DataTable>`), use Svelte 5 snippets instead of raw HTML `<tr>` elements to ensure safe DOM rendering.
- **Native Elements:** ALWAYS use the custom `<Button>` component instead of native `<button>`. Disabled buttons MUST include a `title` attribute for accessibility.

## 4. Styling & Design System (CRITICAL constraints)

- **NO Inline Styles:** Never use `style="..."` attributes. Always use semantic class names and Svelte's scoped `<style>` blocks.
- **Semantic Variables ONLY:** Never hardcode hex codes or raw palette colors (e.g., `var(--gray-50)`). Always map to semantic variables (e.g., `var(--bg-secondary)`, `var(--text-primary)`) to ensure flawless Dark Mode inversion.
- **Intents:**
  - **Solid Intents:** (`--primary-bg`) Use for high-emphasis elements. Always pair with white text.
  - **Subtle Intents:** (`--primary-bg-subtle`) Use for backgrounds/badges. Pair with tinted text (`--primary-text-subtle`).
- **Transparent Hovers:** Never use solid colors for hovering over transparent items. Use alpha overlays (`var(--overlay-hover)`, `var(--overlay-destructive)`).
- **Input Safety:** Text inputs must use the `.input-field` class. Focus states MUST use inset shadows (`box-shadow: inset 0 0 0 1px var(--border-focus)`) to prevent grid/table clipping.

## 5. CSS Compilation & Scope Overrides

- **Svelte CSS Pruning:** Svelte automatically strips "unused" CSS. If styling dynamic content, injected HTML, or elements passed via props (like standard `img` or `svg` icons), you MUST wrap the selector in `:global()` (e.g., `.btn-icon :global(svg)`).
- **Icon Contrast:** Apply `filter: brightness(0) invert(1);` to `:global(img)` and `:global(svg)` inside solid buttons to ensure contrast against dark backgrounds. Do not apply this to text/emojis.
- **Parent-to-Child Layout:** To pass custom spacing to a child, pass a `class` prop (e.g., `class="compact-title"`) and define `:global(.compact-title)` in the parent's style block. Do not build complex prop-based spacing systems.

## 6. Modals, Overlays & Data Flow

- **Modal Construction:** Use `.modal-overlay`, `var(--modal-backdrop)`, `z-index: 1000`, and `backdrop-filter: blur(2px)`.
- **Modal Events:** Always apply `onclick={onCancel}` to the overlay and `e.stopPropagation()` to the modal content window. Use standard callback props (`onCancel`, `onConfirm`).
- **Input Focus:** Use `use:autofocus` on the primary interaction element within a modal.
- **NO `window.prompt()`:** Completely banned. Always use proper modal dialogs and autocomplete components.
- **Data Ingestion:** Bulk data entry MUST NEVER write directly to state. Intercept via `/api/player/check-similarity` and pause with a resolution modal if conflicts exist. Inline player additions must use Autocomplete fetching from `/api/player/all`.

## 7. UI Design System & Layout (The Rule of 8)

- **Strict Rule of 8:** All paddings, margins, gaps, and dimensions must use absolute-reference variables (e.g., `var(--space-8)`, `var(--space-16)`). For non-standard multiples, strictly use explicit math: `calc(var(--space-8) * X)`. Never use "magic numbers" in pixels.
- **Intrinsic Sizing:** Components should not have fixed pixel `width` or `height`. Use padding, standard line-heights, and `max-width` to allow containers to wrap their contents naturally.
- **The Border Exemption:** Border widths are structural lines and are exempt from the Rule of 8. They must use standard `1px` or `2px` values, never a `--space-*` variable.
- **Flexbox Gap over Margins:** Leaf components (e.g., typography, buttons, badges) MUST NOT define their own external margins. Parent layouts must govern spacing exclusively using `display: flex; flex-direction: column; gap: var(--space-16);`. `margin-bottom` is reserved solely for spacing between major structural section wrappers.
- **Pure CSS State Management:** Never use inline JavaScript styles for complex UI states or dynamic colors. Pass primitive boolean props (e.g., `isActive={true}`) from parent to child, and toggle pure CSS classes (e.g., `.node.active`). Use CSS variables to handle internal color shifts.
- **Shorthand Padding:** Always optimize CSS padding (e.g., use `padding: var(--space-16);` instead of `padding: var(--space-16) var(--space-16);`).
