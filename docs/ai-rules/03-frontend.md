---
id: frontend
title: Pillar 3 - Frontend & Svelte 5 Conventions
priority: 30
---

## Frontend Architecture

**Rule:** Use Svelte 5, TypeScript, and Vite as the tech stack.
**Anti-Pattern:** Using alternative frameworks or build tools.

**Rule:** Maintain 400-line soft limit per file and extract sub-domains when exceeded.
**Anti-Pattern:** Creating monolithic files with multiple responsibilities.

**Rule:** Route all UI translations through `frontend/src/i18n.ts`.
**Anti-Pattern:** Hardcoding text strings or using multiple translation systems.

## Component Architecture & Organization

**Rule:** Categorize components in `frontend/src/components/` by responsibility: `ui/` for atomic/domain-agnostic, `modals/` for overlays, `layout/` for structural containers, and `features/` for domain-specific logic.
**Anti-Pattern:** Mixing component types in the same directory or creating unclear categorization.

**Rule:** Design leaf components (Badge, Button, Tooltip, Input) as domain-agnostic with semantic APIs like `variant="info|success|warning|error"`.
**Anti-Pattern:** Using domain names in variant props like `variant="gm|veteran"`.

**Rule:** Design domain layout components (GameTableCard, PlayerList) to accept domain data explicitly with clear props like `gmName`, `tableNumber`, `players`.
**Anti-Pattern:** Over-abstracting with generic snippet APIs or unclear prop interfaces.

**Rule:** For CSS-only abstractions with zero JavaScript logic, extract layout into global CSS utility classes in `style.css` instead of creating Svelte components.
**Anti-Pattern:** Creating Svelte components purely for structural CSS that forces `:global()` usage and breaks encapsulation.

**Rule:** Build Data-Driven Components (like `<DataTable data={rows} columns={config} />`) that own the HTML structure for complex styling needs.
**Anti-Pattern:** Building generic wrapper components that expect raw HTML elements via snippets, breaking Svelte's scoped CSS.

**Rule:** Maintain strict separation between View (read-only) and Edit screens with explicit "Edit" buttons for transitions.
**Anti-Pattern:** Using inline editing hacks like `window.prompt()` in View screens.

**Rule:** Use global utility classes (`.text-strong`, `.table-input`) to ensure typography alignment between plain text and input elements.
**Anti-Pattern:** Relying on automatic font inheritance for inputs and textareas.

## Svelte 5 Patterns

**Rule:** Use `$state`, `$derived`, and `$effect` for reactivity.
**Anti-Pattern:** Using `let` for reactive variables.

**Rule:** Use `:global()` modifier when parent component's scoped CSS needs to affect snippet elements.
**Anti-Pattern:** Assuming scoped CSS automatically applies to snippet content.

**Rule:** Type snippets in generic components using `import type { Snippet } from "svelte"` and `cell?: Snippet<[T, number]>`.
**Anti-Pattern:** Downgrading snippets to string-returning functions that prevent internal Svelte component rendering.

**Rule:** Store global state in `stores.svelte.ts` with loading states using `-1` (unknown) and `0` (loaded).
**Anti-Pattern:** Scattering state management across multiple files or inconsistent loading conventions.

**Rule:** Use global utility classes (`.group`, `.group-hover-reveal`) for group hover reveal patterns.
**Anti-Pattern:** Implementing hover reveal logic in individual Svelte components.

## Styling & Theming

**Rule:** Use global CSS variables like `var(--info-bg)` and `var(--tooltip-bg)` instead of hardcoded hex colors.
**Anti-Pattern:** Hardcoding color values in components.

**Rule:** Use flexbox for panels and CSS Grid for complex list alignment.
**Anti-Pattern:** Using inappropriate layout systems for the use case.

**Rule:** Use inverted schemes (dark background + light text) for floating elements like tooltips and popovers.
**Anti-Pattern:** Using the same color scheme for both main content and floating elements.

## Component API Design

**Rule:** Use visual props (variant, size, fill, iconOnly) to control appearance only.
**Anti-Pattern:** Bundling layout behavior into visual props.

**Rule:** Use layout props (fixedWidth, align, spacing) to control behavior only.
**Anti-Pattern:** Mixing visual and behavioral concerns in single props.

## Frontend Coding Standards

**Rule:** Use `logger.info()`, `logger.warn()`, and `logger.error()` from `src/utils/logger.ts` for all logging.
**Anti-Pattern:** Using `console.log()` for debugging or logging purposes.

**Rule:** Always import and use the Button component instead of native `<button>` tags.
**Anti-Pattern:** Using native HTML button elements directly.

**Rule:** Include `title` attribute for disabled buttons to provide context.
**Anti-Pattern:** Leaving disabled buttons without explanatory tooltips.

## Modal & Overlay Patterns

**Rule:** Use `.modal-overlay` utility and `--modal-backdrop` variable for modal overlays.
**Anti-Pattern:** Creating custom overlay implementations without consistent styling.

**Rule:** Set modal z-index to `1000` to escape `SidePanel` stacking contexts.
**Anti-Pattern:** Using insufficient z-index values that get covered by other UI elements.

**Rule:** Apply `backdrop-filter: blur(2px)` for visual depth in modal overlays.
**Anti-Pattern:** Using flat or unstyled modal backgrounds.

**Rule:** Implement `onclick={onCancel}` on overlay and `e.stopPropagation()` on modal content.
**Anti-Pattern:** Missing proper event handling that causes modal closing issues.

**Rule:** Use `use:autofocus` on the primary input/textarea in modals.
**Anti-Pattern:** Forgetting to focus the primary interaction element.

**Rule:** Use standard callback props like `onImport`, `onCancel`, or `onConfirm` for modal actions.
**Anti-Pattern:** Creating inconsistent modal prop interfaces.

## Data Entry & UI Flow Patterns

**Rule:** Bulk data ingestion must never write directly to table state without validation; always intercept via `/api/player/check-similarity` and pause with modal if conflicts exist.
**Anti-Pattern:** Allowing unvalidated bulk data to bypass similarity checks and modal interruption.

**Rule:** When passing dynamic rows into generic components like `DataTable`, use Svelte 5 snippets (e.g., `footerRow`) instead of raw HTML `<tr>` elements for safe `<tbody>` rendering.
**Anti-Pattern:** Passing raw HTML elements that break table structure and Svelte's rendering system.

**Rule:** Always use inline Svelte 5 Autocomplete components that fetch from `/api/player/all` and rehydrate history.
**Anti-Pattern:** Using native browser prompts or custom input implementations without autocomplete functionality.

**Rule:** Completely ban the use of `window.prompt()` in favor of proper modal dialogs and autocomplete components.
**Anti-Pattern:** Using native browser prompts for any user input scenarios.
