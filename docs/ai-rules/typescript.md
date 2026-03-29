---
id: typescript
title: TypeScript + Svelte Scoped Instructions
scope: language
priority: 80
applyTo:
  - frontend/src/**
outputs:
  copilot: .github/typescript.instructions.md
toolNotes:
  copilot: Scoped instructions for frontend TS/Svelte changes.
---
# TypeScript + Svelte Instructions — Organizador Diplomacy

## Stack
TypeScript 5 (strict) · bun · ESLint 9 (typescript-eslint v8 `strictTypeChecked`) · Vitest 4 · @testing-library/dom

> Scoped instructions: `typescript.md` (applyTo `frontend/src/**`) contain language-specific detail.

## Svelte 5 conventions
- Use `$state` runes for reactive state, not `let` variables that get reassigned.
- Use `$derived` for computed values.
- Use `$effect` for side effects.
- Props defined with `$props()` runes.
- Event handlers use `onclick={() => ...}` syntax.
- Bindings use `bind:value={variable}` syntax.

## Component conventions
- Export component name via `<script lang="ts">` and file name.
- Use PascalCase for component names.
- Props typed with TypeScript interfaces.
- Slots used for composition.
- Never use native HTML `<button>` tags for actions. Always import and use universal `<Button>` component (`import Button from './Button.svelte'`).
- Use orthogonal props to control button appearance: `variant` ('primary', 'secondary', 'success', 'warning', 'ghost'), `size` ('md', 'sm'), `fill` (boolean, to take full width of container), and `iconOnly` (boolean).

## Constraint-Preserving UI (The Swap Pattern)
- When manipulating strict arrays (like 7 players per table), use `SwapTarget` pattern instead of generic "Move to table" dropdowns.
- Users click two entities to swap their positions, preserving mathematical constraints.
- Maintain table integrity while allowing flexible player movement.

## Handling Nulls
- When dealing with optional backend data (like `pais: null`), `<select>` dropdowns must explicitly handle `null` state.
- Use `<option value={null}>🎲 Aleatorio</option>` for optional selections.
- Ensure `bind:value={j.pais}` correctly selects "🎲 Aleatorio" when `j.pais` is empty/null.

## Custom Tooltips
- Avoid native HTML `title="..."` attributes for complex information due to slow delays.
- Use custom CSS hover popovers (e.g., `.tooltip-popover`) for instant feedback.
- Structure: `<div class="reason-tooltip"><span class="info-icon">ℹ️</span><div class="tooltip-popover">{content}</div></div>`.
- CSS: `z-index: 9999` for proper layering.

## Build & Tooling
- Vite entry: `src/index.html` → `static/`.
- Commands: `bun run build`, `bun run dev`, `bun run typecheck`, `bun run lint`.
- Rules: `bun run ai-rules:generate`.

## Testing
- Vitest + `@testing-library/svelte`.
- Co-located tests: `ComponentName.test.ts`.
- Mock API: `vi.mock('../api')`.
- Test files: `frontend/src/*.test.ts`.
- DOM testing for buttons MUST use accessible queries: `screen.getByRole('button', { name: /Text/i })`. Do NOT use `getByText()` for buttons, as emojis and text are structurally separated in DOM.
- For `iconOnly` buttons, rely on their `title` attribute, which `getByRole` automatically uses as accessible name.

## Naming
- Variables/Functions: `camelCase`.
- Svelte 5 Props: `camelCase` (starting with "on" for handlers).
- Domain Types: `PascalCase`.
- Backend Mapping: `snake_case` allowed for API properties.

## CSS
- Flex layout for panels, rows, containers.
- `overflow: hidden; text-overflow: ellipsis; white-space: nowrap;` for truncation.
- Component-specific UI classes (like button variants or layouts) must live in scoped `<style>` blocks within component. Keep `static/style.css` strictly for CSS variables, CSS resets, and high-level layout utilities.
- Scoped `<style>` in `.svelte` files.
- `static/style.css` for variables, resets, utility classes.
- Layout pattern: Always use the <PanelLayout> component with {#snippet body()}, {#snippet header()}, and {#snippet footer()} for side panel content. Use scrollable={false} for table views relying on .flex-table-wrap. Do not manually write .panel-scroll, .panel-body-fixed, or .panel-footer classes.
