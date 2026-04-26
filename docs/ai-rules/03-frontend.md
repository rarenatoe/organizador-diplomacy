---
id: frontend
title: Pillar 3 - Frontend, Svelte 5 & UI
priority: 30
---

## 1. Svelte 5 Reactivity & State

- **Runes ONLY:** USE `$state`, `$derived`, `$effect`. BANNED: `let` for reactivity, ES6 Classes for state.
- **State Architecture:** Group related states in Discriminated Unions. Extract complex state into POJOs using `lowerCamelCaseState.svelte.ts` files. Use an array stack for navigation.
- **Thick Logic Extraction:** Complex data mutations (e.g., drag-and-drop, multi-array swapping, draft orchestrations) MUST be extracted into a dedicated `.svelte.ts` controller. NEVER leave massive (50+ line) mutation functions inside `.svelte` script blocks.
- **Deterministic State Rebuilding:** When users perform complex mutations (like multi-array swaps), NEVER surgically patch array indexes (which causes duplicates). Always re-run a deterministic mathematical pass over the entire state to rebuild derived lists.
- **Declarative Transformations:** Use modern declarative chains (`Object.values().map().filter().sort()`) instead of imperative `for...in` loops to derive state.
- **Loop Constants:** ALWAYS use Svelte's `{@const ...}` to compute derived target objects or parameters within `{#each}` loops. NEVER instantiate new objects inline inside HTML event handlers (e.g., `onclick={() => fn({ id })}`).
- **Typing:** Use component-level Generics (`<script lang="ts" generics="...">`) so components adapt safely to diverse data shapes.
- **Snippet Event Handlers:** NEVER use inline arrow functions for event handlers inside HTML elements within Svelte 5 `{#snippet}` blocks or `{#each}` loops (e.g., `onchange={(e) => update(i)}`). ALWAYS declare them first using `{@const handleChange = (e: Event) => update(i)}` and pass the reference. This ensures strict Svelte 5 architectural compliance and prevents reactive instantiation bugs.
- **Immutable Array Mutations:** BANNED: `Array.prototype.splice()`. NEVER mutate array states surgically. To remove an item, ALWAYS rebuild the array deterministically using `.filter((_, i) => i !== targetIndex)`.

## 2. Auto-Generated SDK (`@hey-api`)

- **Single Source of Truth:** Import all domain types from `src/generated-api`. BANNED: Manual `fetch` calls, manual domain interfaces in `src/types.ts`.
- **Response Unpacking:** ALWAYS unpack immediately: `const { data, error } = await apiEndpoint()`. Handle `error` explicitly.
- **Error Handling:** Intercepted globally in `api/client.ts`. Use typed unions for error parsers, NEVER `any`/`unknown`.

## 3. Layout & CSS Grid (Rule of 8)

- **Styling:** Pure CSS only. Use semantic variables (`var(--space-8)`). BANNED: Tailwind, utility classes, inline `style="..."`.
- **Class Injection:** Use `cx()`/`clsx`. BANNED: String concatenation.
- **Intrinsic Sizing:** Leaf components MUST NOT define external margins. Parents dictate spacing via `display: flex; gap: ...`. Wrap target selectors in `:global()`.
- **Grid Blowout:** Apply `min-width: 0` to flex containers and children inside CSS Grids.
- **Structural Abstractions:** Create wrapper components (`<PanelSection>`) instead of copy-pasting layout classes.

## 4. UI Architecture & UX

- **Smart vs Dumb Components:** `features/` are Smart components that handle API side-effects and complex state orchestration. `ui/` and `layout/` are Dumb components that MUST remain domain-agnostic and bubble actions via callback props. NEVER perform API calls in Dumb components.
- **References:** Swap entire object references for complex nested objects. BANNED: Deep mutations of nested properties.
- **Snippets:** Presentation lists must be dumb. Use Svelte 5 Snippets to yield domain logic (indices, IDs) back to the parent. Abstract entire list containers, not just leaf items.
- **UX Guards:** Mimic padding in read-only states and set `min-height` to prevent layout shifts. NEVER use UI-layer fallbacks (e.g., `{cupos ?? deseadas}`) to mask inaccurate underlying data; fix the mathematical source of truth. Pair floating UI visibility with explicit interaction booleans to prevent zombies.
- **Banned Browser APIs:** NEVER use `window.prompt()`, `window.alert()`, or `window.confirm()`. ALWAYS use custom modal components.
- **Dates:** Cast naive backend timestamps to UTC (`+ "Z"`) before parsing to adapt to local timezones. ALWAYS use the shared `formatDate` utility from `src/i18n.ts`.
