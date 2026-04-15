---
title: Pillar 3 - Frontend & Svelte 5 Conventions
priority: 30
---

## 1. Core Architecture & Svelte 5 Reactivity

- **Stack:** STRICTLY Svelte 5, TypeScript, Vite. NEVER use other frameworks.
- **Runes ONLY:** USE `$state`, `$derived`, `$effect`. NEVER use `let` for reactive state.
- **Derived State:** USE `$derived.by(() => {...})` for complex logic. NEVER use nested ternaries.
- **Context Adaptation:** USE `$derived` (e.g., `isEditing = $derived(id !== null)`) to adapt a single component for Create/Edit views.
- **Component Routing:** Categorize strictly. `ui/` MUST be domain-agnostic (e.g., `variant="danger"`). `features/` MUST be domain-aware (e.g., `player={player}`).
- **Logging:** ALWAYS use `logger.info()`, `warn()`, and `error()` from `src/utils/logger.ts`. NEVER use `console.log()`.

## 2. Layout, CSS Grid & The Rule of 8

- **Strict Rule of 8:** ALL paddings, margins, gaps, and dimensions MUST use absolute-reference variables (`var(--space-8)`). For non-standard multiples, use `calc(var(--space-8) * X)`. Border widths (`1px`) are the ONLY exception.
- **The Border Exemption:** Border widths (`1px` or `2px`) are structural lines and are EXEMPT from the Rule of 8.
- **Svelte CSS Pruning:** Svelte strips "unused" CSS. WHEN styling dynamic content, injected HTML, or standard `<svg>` elements, you MUST wrap the selector in `:global()` (e.g., `.btn-icon :global(svg)`).
- **Icon Contrast:** ALWAYS apply `filter: brightness(0) invert(1);` to `:global(img)` and `:global(svg)` inside solid primary buttons to ensure contrast against dark backgrounds.
- **The Flexbox-in-Grid Blowout:** When nesting a `display: flex` container inside a CSS Grid column, flex items default to `min-width: auto` and blow out `minmax()` constraints. ALWAYS apply `min-width: 0` to both the flex container and its flex children.
- **Ghost Cells for Tabular Grids:** NEVER conditionally omit structural grid cells. If data is null, omit the content but render the empty wrapper `div` cell to prevent trailing elements from sliding into the wrong columns.
- **Zero Layout Shift:** When toggling a component between an editable state (`<input>`) and a read-only state (`<span>`), the read-only element MUST mimic the exact padding, height, and margins of the input field.
- **Intrinsic Sizing:** Components MUST NOT have fixed pixel `width` or `height`. Use padding, standard line-heights, and `max-width` to allow containers to wrap their contents naturally.
- **Flexbox Gap over Margins:** Leaf components (typography, buttons, badges) MUST NOT define their own external margins. Parent layouts must govern spacing exclusively using `display: flex; gap: var(--space-X);`.

## 3. UI Design System & Component API

- **Pure CSS ONLY:** NEVER use Tailwind or utility classes. NEVER use `style="..."`. Wrap dynamic DOM target selectors in `:global()` (e.g., `:global(svg)`).
- **Semantic Variables:** ALWAYS map colors to semantic variables (e.g., `var(--bg-secondary)`). NEVER hardcode hex codes to guarantee Dark Mode inversion.
- **Reference Swapping over Mutation:** When exchanging complex nested objects between UI elements, swap the entire object reference. NEVER manually overwrite individual properties, as this silently destroys auxiliary metadata (like tooltips).
- **Snippets over HTML:** USE `import type { Snippet }` and Svelte snippets instead of raw HTML strings for dynamic rendering.

## 4. Product UX & Signal-to-Noise

- **Gestalt Proximity (Wrapper Tooltips):** Do not force standalone icons (`ℹ️`) next to elements if the data relates directly to the element. `<Tooltip>` components MUST accept Svelte Snippets (`children`) to invisibly wrap components, turning the element itself into the hover surface.
- **Zero-Delay Data Discovery:** NEVER rely on the native HTML `title` attribute for critical data discovery (it has an OS-forced 500ms delay). ALWAYS use custom JS/Svelte popover components.
- **Contextual Metadata:** Hide administrative metadata (like Notion link indicators) in read-only domain summaries. Expose props (e.g., `showNotionIndicator={false}`) to keep layouts focused on domain output.
- **Concise Badges:** Keep badge text categorical (`"Antiguo"`). Push verbose supplementary data (`"15 juegos"`) into Wrapper Tooltips.

## 5. State & Data Flow

- **The Navigation Stack Pattern:** USE an in-memory stack (array in `.svelte.ts`) for multi-level navigation. NEVER use flat variables (`$state(panelId)`), as this leads to hardcoded "Back" logic.
- **Modals:** USE `.modal-overlay`, `var(--modal-backdrop)`. ALWAYS apply `onclick={onCancel}` to overlay and `e.stopPropagation()` to content.
- **Input Focus:** ALWAYS use `use:autofocus` on the primary interaction element within a modal or panel.
- **Banned Browser APIs:** NEVER use `window.prompt()`, `window.alert()`, or `window.confirm()`. ALWAYS use proper custom modal components.
- **Encapsulate State:** Do not pollute layout components (`App.svelte`) with business logic. Extract complex state into singleton classes in `.svelte.ts` files.
- **Data Ingestion:** Bulk data entry MUST NEVER write directly to state. Intercept via `/api/player/check-similarity` and present `SyncResolutionModal` if conflicts exist.
