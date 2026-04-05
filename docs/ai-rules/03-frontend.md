---
id: frontend
title: Pillar 3 - Frontend & Svelte 5 Conventions
priority: 30
---

## Svelte 5 Runes & State

- **Reactivity:** Exclusively use `$state`, `$derived`, and `$effect`. Do not use `let` for variables that require reactivity but are not in `$state`.
- **Global Stores:** Found in `stores.svelte.ts`. UI components must use store getters directly in templates. No local copies of store state.
- **Loading States:** Use `-1` for unknown state; `0` when loaded.
- **Handlers & Bindings:** Use `onclick={() => ...}` syntax for events and `bind:value={var}` for bindings.

## Frontend Coding Standards

- **Logging Only:** NEVER use `console.log()` for any purpose. All debugging and error logging must use the custom logger from `src/utils/logger.ts` with appropriate methods (`logger.info()`, `logger.warn()`, `logger.error()`).

## UI Components & Styling

- **Buttons:** NEVER use native HTML `<button>` tags for actions. Always import and use the universal `<Button>` component (`import Button from './Button.svelte'`). Use orthogonal props to control appearance: `variant` ('primary', 'secondary', 'success', 'warning', 'ghost'), `size` ('md', 'sm'), `fill`, and `iconOnly`. Give disabled buttons a `title` attribute for user feedback.
- **Layouts:** Use the `<PanelLayout>` component with `{#snippet body()}`, `{#snippet header()}`, and `{#snippet footer()}` for side panel content.
- **CSS:** Use flex layout for panels. Strictly prefer **CSS Grid** (`display: grid`) over Flexbox when aligning lists with complex horizontal alignment (e.g., player tables, waiting lists). Use scoped `<style>` in components.

## Domain Patterns

- **Constraint-Preserving UI (The Swap Pattern):** When manipulating strict arrays (like exactly 7 players per table), use the `SwapTarget` pattern. Users must click two entities to swap their positions to preserve mathematical constraints.
- **Handling Nulls:** Dropdowns interacting with optional backend data (e.g., `pais: null`) must explicitly handle nulls (e.g., `<option value={null}>🎲 Aleatorio</option>`).
- **Tooltips:** Avoid native `title="..."` attributes for complex information due to slow delay. Use custom CSS hover popovers (`.reason-tooltip` containing a `.tooltip-popover`).
