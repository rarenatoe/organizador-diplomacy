<!-- GENERATED FILE: DO NOT EDIT DIRECTLY -->
<!-- Source of truth: docs/ai-rules/*.md -->
---
description: TypeScript + Svelte Scoped Instructions
globs: frontend/src/**
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

## Naming
- Variables/Functions: `camelCase`.
- Svelte 5 Props: `camelCase` (starting with "on" for handlers).
- Domain Types: `PascalCase`.
- Backend Mapping: `snake_case` allowed for API properties.

## CSS
- Flex layout for panels, rows, containers.
- `overflow: hidden; text-overflow: ellipsis; white-space: nowrap;` for truncation.
- Scoped `<style>` in `.svelte` files.
- `static/style.css` for variables, resets, utility classes.
- Scroll pattern: `.panel-body` (flex column, hidden) + `.panel-scroll` (flex 1, auto scroll).
