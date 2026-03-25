<!-- GENERATED FILE: DO NOT EDIT DIRECTLY -->
<!-- Source of truth: docs/ai-rules/*.md -->
---
applyTo: "frontend/src/**"
---

## Svelte 5 conventions
- Domain interfaces in `src/types.ts`.
- Runes: `$state` (reactive), `$derived` (computed), `$effect` (side effects), `$props` (props), `$bindable` (two-way).
- State: `src/stores.svelte.ts` (singleton `appState`). Use getters/setters.
- API: `src/api.ts` (centralized fetch calls).
- Structure: `src/components/*.svelte`. No import cycles.
- Children: Use `Snippet` type and `{@render children()}`.

## Component conventions
- Error handling: use `onShowError(title, output)` callback.
- Event handling: use `onclick={handler}` in markup.
- Control flow: `{#if}`, `{#each}`, `{#await}`.
- Recursive: use self-imports (e.g., `import SnapshotNode from './SnapshotNode.svelte'`).

## Build & Tooling
- Vite entry: `src/index.html` → `static/`.
- Commands: `bun run build`, `bun run dev`, `bun run typecheck`, `bun run lint`.
- Rules: `bun run ai-rules:generate`.

## UI & State
- Global IDs from `graph_nodes` (numeric).
- Selection: `setSelectedSnapshot(id)` → `.csv-selected` highlight.
- Nodes: Snapshot nodes render chain recursively; branches stacked vertically.

## Testing
- Vitest + `@testing-library/svelte`.
- Co-located tests: `ComponentName.test.ts`.
- Mock API: `vi.mock('../api')`.

## Naming
- Variables/Functions: `camelCase`.
- Svelte 5 Props: `camelCase` (starting with "on" for handlers).
- Domain Types: `PascalCase`.
- Backend Mapping: `snake_case` allowed for API properties.
