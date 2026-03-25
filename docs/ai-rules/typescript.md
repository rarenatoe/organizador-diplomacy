---
id: typescript
title: TypeScript + Svelte Scoped Instructions
scope: language
applyTo:
  - frontend/src/**
priority: 80
outputs:
  copilot: .github/typescript.instructions.md
  trae: .trae/rules/typescript.md
toolNotes:
  copilot: Scoped instructions for frontend TS/Svelte changes.
  trae: Auto-attached for frontend/src/** files.
---

## Svelte 5 conventions
- All domain interfaces live in `src/types.ts` — export everything from there.
- Use Svelte 5 runes: `$state` for reactive state, `$derived` for computed values, `$effect` for side effects, `$props` for component props.
- State management: `src/stores.svelte.ts` — class-based `AppState` with `$state` runes, exported as singleton `appState`. Use getter/setter functions (e.g., `getSelectedSnapshot()`, `setSelectedSnapshot()`).
- API layer: `src/api.ts` — centralized fetch calls (fetchChain, fetchSnapshot, fetchGame, runScript, detectSync, confirmSync, etc.).
- Component structure: `src/components/*.svelte` — each component is a single `.svelte` file with `<script>`, markup, and optional `<style>` blocks.
- Import graph (no cycles): `App.svelte` → components, stores, api. Components → stores, api, types. Stores → types only.

## Svelte component conventions
- Use `$props()` to declare component props with TypeScript interfaces.
- Use `$state` for local reactive state within components.
- Use `$derived` for computed values (e.g., `let disabled = $derived(syncing || running)`).
- Use `$effect(() => { ... })` for side effects (e.g., loading data on mount).
- Use `$bindable()` for two-way binding when needed.
- **Error Handling**: Async actions in components should use an `onShowError(title, output)` callback to display errors in the main App modal.
- Event handling: use `onclick={handler}` directly in markup (not `addEventListener`).
- Use `{#if}`, `{#each}`, `{#await}` blocks for control flow.
- Use `{@render children()}` for slot content (not `<slot>` — deprecated in Svelte 5).
- For recursive components, use self-imports (e.g., `import SnapshotNode from './SnapshotNode.svelte'`) instead of `<svelte:self>`.

## Build & tooling
- Vite builds from `src/index.html` entry point → `static/` output directory.
- Run `bun run build` to build with Vite and copy `index.html` to `templates/`.
- Run `bun run dev` for development server with HMR.
- Run `bun run typecheck` for type-only check.
- Run `bun run lint` — ESLint strict.
- **Rules Generation**: Run `bun run ai-rules:generate` (alias for `bun run scripts/generate-ai-instructions.ts`) to propagate changes from `docs/ai-rules/` to the rest of the workspace.
- Svelte files use `<script lang="ts">` for TypeScript support.

## UI conventions
- `templates/index.html` is the production HTML served by Flask (copied from build output).
- `src/index.html` is the Vite entry template with `<div id="app">` mount point.
- Component-specific CSS belongs in `<style>` blocks within the `.svelte` files. Global variables and utilities live in `static/style.css` imported in `App.svelte`.
- **Global IDs**: Selection and routing use raw numeric IDs from the `graph_nodes` backend table.
- **Click-to-select**: snapshot node click → `setSelectedSnapshot(id)` → `.csv-selected` green ring + button label "Organizar · #N".
- Game node click → `openGame(id)` → fetches game detail, shows in SidePanel.
- Sync node click → `openSync(id)` → fetches sync metadata, shows in SidePanel.
- `handleRunScript("organizar")` reads selection from stores. `deselectSnapshot()` resets.
- `SnapshotNode.svelte` renders the chain recursively using self-import — branches stacked vertically.

## Testing conventions
- Use Vitest with `@testing-library/svelte` for component testing.
- Test files co-located with components: `ComponentName.test.ts` next to `ComponentName.svelte`.
- Mock API calls with `vi.mock('../api')`.
- Use `render()` from `@testing-library/svelte` to mount components in tests.
- **Component typing in tests**: `render()` returns `any`-typed component. Avoid `as unknown as` double casts (code smell). Prefer testing via DOM queries instead of component instance.

## Svelte 5 children pattern
- For components with children, import `Snippet` type from "svelte" and declare `children: Snippet` in Props interface.
- Use `{@render children()}` in template (not `<slot />` — deprecated).

## Naming Conventions
- **Variables & Functions:** Always use `camelCase`.
- **Svelte 5 Event Props:** Custom event handlers passed as component props MUST use strict `camelCase` starting with "on" (e.g., `onNewDraft`, `onChainUpdate`, `onOpenSnapshot` — *never* `onnewdraft`). Native DOM events remain all-lowercase (e.g., `onclick`, `onkeydown`).
- **Domain Types:** Use `PascalCase` for Interfaces and Types.
- **Backend API Mapping:** Object properties mapped directly from the backend JSON API (like `created_at`, `juegos_este_ano`) are the **only** permitted exceptions where `snake_case` is allowed in TypeScript.
