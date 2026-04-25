---
id: frontend
title: Pillar 3 - Frontend, Svelte 5 & UI
priority: 30
---

## 1. Svelte 5 Reactivity & State

- **Runes ONLY:** USE `$state`, `$derived`, `$effect`. NEVER use `let` for reactive state. Use `$derived.by()` for complex logic.
- **Functional POJO State:** Extract complex state into plain objects using Runes, NEVER ES6 Classes.
- **Discriminated Unions:** Group related state variables (e.g., `status: 'idle' | 'resolving'`) into Discriminated Unions to eliminate impossible states.
- **Navigation Stack:** USE an in-memory stack (array) for multi-level navigation. NEVER use flat variables (`$state(panelId)`).
- **Logic File Naming:** NEVER name a logic file identically to a UI file (e.g., avoid `Component.svelte` and `Component.svelte.ts`). Use `lowerCamelCaseState.svelte.ts` to prevent bundler collisions.
- **Component-Level Generics:** Use component-level Generics (`<script lang="ts" generics="T extends {...}">`) so components adapt safely to diverse data shapes.

## 2. Auto-Generated API SDK (CRITICAL)

- **NO MANUAL FETCHING:** NEVER write manual `fetch` calls or custom interfaces. ALWAYS use the `@hey-api` generated endpoints (e.g., `apiPlayerCheckSimilarity`) and types from `frontend/src/generated-api`.
- **SDK as Single Source of Truth:** The generated SDK (`frontend/src/generated-api`) is the ABSOLUTE single source of truth for all domain types. NEVER manually define domain interfaces (e.g., `Game`, `Player`, `DraftResponse`) in `src/types.ts` or any other file. ALL domain types MUST be imported exclusively from `frontend/src/generated-api`. `src/types.ts` is reserved ONLY for purely UI-local types (e.g., `ToastState`, `EditPlayerRow`) that have no backend equivalent.
- **Explicit Response Unpacking:** ALWAYS unpack the `@hey-api` standardized response tuple immediately at the call site: `const { data, error } = await apiEndpoint()`. NEVER pass the raw response object to child components. Handle `error` explicitly before using `data`.
- **Global Error Handling:** FastAPI `422 ValidationErrors` are intercepted/normalized in `api/client.ts`. UI components MUST safely read `response.error` as a clean string. Legacy `api.ts` is DEPRECATED.

## 3. Layout, CSS Grid & The Rule of 8

- **Strict Rule of 8:** ALL spacing uses absolute variables (`var(--space-8)`). Borders (`1px`) are the ONLY exemption.
- **Pure CSS ONLY:** NEVER use Tailwind, utility classes, or inline `style="..."`. Use semantic variables (`var(--bg-secondary)`).
- **Class Injection:** ALWAYS use `cx()` or `clsx` for dynamic classes. NEVER use string concatenation (`class="{base} {active}"`).
- **Flexbox-in-Grid Blowout:** Apply `min-width: 0` to flex containers AND children inside CSS Grids to prevent `minmax()` blowout.
- **Svelte CSS Pruning:** Wrap dynamic target selectors in `:global()` (e.g., `.btn-icon :global(svg)`).
- **Sticky Stacking Contexts:** Elements inside `position: sticky` are trapped in its stacking context. To make an absolute child (like a dropdown) overlap, you MUST elevate the parent cell's z-index on focus/hover.
- **Intrinsic Sizing:** Leaf components MUST NOT define their own external margins. Parent layouts must govern spacing exclusively using `display: flex; gap: ...`.

## 4. UI Architecture & UX

- **Component Routing:** `ui/` MUST be domain-agnostic. `features/` MUST be domain-aware.
- **Reference Swapping:** When exchanging complex nested objects, swap the entire object reference. NEVER manually overwrite individual properties.
- **Zero Layout Shift:** Read-only states (`<span>`) MUST mimic the exact padding/height of editable states (`<input>`).
- **Action Bubbling:** Feature components MUST bubble actions via callback props. NEVER perform API side-effects deeply in nested UI components.
- **Data Discovery:** NEVER rely on native HTML `title` attributes. ALWAYS use `<Tooltip>` components wrapping Svelte Snippets.
- **Banned Browser APIs:** NEVER use `window.prompt()`, `window.alert()`, or `window.confirm()`. ALWAYS use custom modal components.
- **Floating UI Guard:** Do not base the visibility of floating elements (dropdowns, modals) solely on derived array lengths. ALWAYS pair visibility with an explicit user-interaction boolean (e.g., `isActive`) to prevent zombie UI elements.
- **Logging:** ALWAYS use `logger.info()` from `src/utils/logger.ts`. NEVER use `console.log()`.
