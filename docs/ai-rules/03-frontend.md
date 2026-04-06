---
id: frontend
title: Pillar 3 - Frontend & Svelte 5 Conventions
priority: 30
---

## Frontend Architecture (CRITICAL)

**TECH STACK**: Svelte 5, TypeScript, Vite
**FILE LIMIT**: 400 lines per file (extract sub-domains when exceeded)
**TRANSLATION**: All UI translations go through `frontend/src/i18n.ts`

## Component Architecture & Organization (CRITICAL)

**FOLDER HIERARCHY:**
Categorize all components in `frontend/src/components/` by responsibility:

- `ui/`: Atomic/domain-agnostic (e.g., `Button`, `Badge`).
- `modals/`: Overlays using the `.modal-overlay` pattern.
- `layout/`: Structural containers (e.g., `SidePanel`, `DataTable`).
- `features/`: Domain-specific logic (e.g., `SnapshotDraft`, `GameNode`).

**LEAF COMPONENTS** (Domain-Agnostic):

- `Badge`, `Button`, `Tooltip`, `Input` - NO domain logic
- Use semantic APIs: `variant="info|success|warning|error"`
- NEVER use domain names: `variant="gm|veteran"`

**DOMAIN LAYOUT COMPONENTS** (Domain-Specific):

- `GameTableCard`, `PlayerList` - Accept domain data explicitly
- Use clear props: `gmName`, `tableNumber`, `players`
- AVOID over-abstracting with generic snippet APIs

- **CSS-Only Abstractions vs. Components:** If a planned "component" has zero JavaScript logic and exists purely to apply structural CSS to injected HTML children (like a generic Table wrapper), DO NOT create a Svelte Component for it. This forces the use of `:global()` CSS which breaks encapsulation and snippet rendering. Instead, extract the layout into a global CSS utility class in `style.css` (e.g., `.data-table`) and use native HTML elements in the consumer.

- **Data-Driven Components over CSS Wrappers:** To style complex children (like tables with sticky columns), build **Data-Driven Components** (e.g., `<DataTable data={rows} columns={config} />`) that own the HTML structure (`<table>`, `<tr>`, `<td>`). DO NOT build generic wrapper components that expect raw HTML elements passed via snippets, as this breaks Svelte's scoped CSS and forces `:global()` code smells.

- **Strict View vs. Edit Separation:** Do not blur boundaries between View (read-only) and Edit screens. A View screen MUST NOT contain inline editing hacks like `window.prompt()`. Provide an explicit "Edit" button that transitions the user to a dedicated Draft/Edit screen with proper form inputs.

- **Input Typography Inheritance:** HTML `<input>` and `<textarea>` elements do not inherit `font-family` or `font-weight` automatically. Use global utility classes in `style.css` (e.g., `.text-strong`, `.table-input`) to ensure typography perfectly aligns between plain text in View modes and inputs in Edit modes.

## Svelte 5 Patterns (CRITICAL)

**REACTIVITY**:

- USE: `$state`, `$derived`, `$effect`
- AVOID: `let` for reactive variables

**SNIPPETS & CSS SCOPING** (CRITICAL):

- Parent → Child snippet injection: Child's scoped CSS **WILL NOT** affect snippet elements
- SOLUTION: Use `:global()` modifier: `:global(.table-wrap td) { ... }`
- FAILURE: Results in stripped styles and broken layouts

**TYPING SNIPPETS IN GENERICS** (CRITICAL):

- When passing Svelte 5 snippets to a generic component (like a table cell renderer), you MUST import and use the official Svelte type: `import type { Snippet } from "svelte";` and type it as `cell?: Snippet<[T, number]>`.
- DO NOT downgrade snippets to string-returning functions (e.g., `(row: T) => string`), as this makes it impossible to render internal Svelte components (like Badges) inside the snippet.

**STORES & STATE**:

- Global stores: `stores.svelte.ts`
- Loading states: `-1` (unknown), `0` (loaded)
- Event handlers: `onclick={() => ...}`
- Bindings: `bind:value={variable}`

**Group Hover Reveal** - Use global utility classes (`.group`, `.group-hover-reveal`) to show/hide secondary actions like delete buttons. This avoids Svelte CSS isolation issues and keeps components DRY.

## Styling & Theming

**COLOR SYSTEM**:

- NEVER use hardcoded hex colors
- USE global CSS variables: `var(--info-bg)`, `var(--tooltip-bg)`
- DEFINED in: `frontend/static/style.css`

**LAYOUT SYSTEM**:

- Panels: Use flexbox
- Lists: Prefer CSS Grid over Flexbox for complex alignment
- Components: Use scoped `<style>` blocks

**FLOATING ELEMENTS**:

- Tooltips, popovers, toasts: Use inverted schemes
- Dark background + light text = maximum Z-axis contrast

**Theme Integrity** - Never hardcode hex colors in components. Always define semantic variables in `style.css` (e.g., `--danger`, `--success`) and reference them in component styles.

## Component API Design

**VISUAL PROPS**: Control appearance only

- `variant`, `size`, `fill`, `iconOnly`

**LAYOUT PROPS**: Control behavior only

- `fixedWidth`, `align`, `spacing`

**SEPARATION**: Never bundle layout behavior into visual props

- WRONG: `pill` prop that controls width
- RIGHT: `fixedWidth={true}` + `pill={true}`

## Frontend Coding Standards

**LOGGING**:

- NEVER use `console.log()`
- USE: `logger.info()`, `logger.warn()`, `logger.error()`
- IMPORT: `src/utils/logger.ts`

**BUTTONS**:

- NEVER use native `<button>` tags
- ALWAYS import: `import Button from './Button.svelte'`
- REQUIRED: `title` attribute for disabled buttons

## Testing Strategy

**FRAMEWORK**: Vitest + `@testing-library/svelte`

**DOM QUERIES**:

- Buttons: `screen.getByRole('button', { name: /Text/i })`
- NEVER: `getByText()` for buttons (emojis separated from text)
- Icon-only buttons: Use `title` attribute for accessible name

**STATE MOCKING**:

- NEVER: `vi.mock()` on `.svelte.ts` files with `$state` runes
- USE: Integration-style testing for state files

**TEST MAINTENANCE**:

- CSS class changes → IMMEDIATELY update test queries
- Search for: `querySelector`, `closest`, `getBy` calls

## Modal & Overlay Patterns (CRITICAL)

**VISUAL CONTRACT:**

- **Overlay:** MUST use `.modal-overlay` utility and `--modal-backdrop` variable.
- **Z-Index:** Set to `1000` to escape `SidePanel` (z-index 50) stacking contexts.
- **Effect:** Apply `backdrop-filter: blur(2px)` for depth.

**BEHAVIORAL CONTRACT:**

- **Events:** Implement `onclick={onCancel}` on overlay and `e.stopPropagation()` on content.
- **Focus:** Use `use:autofocus` on the primary input/textarea.
- **Props:** Use standard callbacks like `onImport`, `onCancel`, or `onConfirm`.

**EXAMPLES:**

```svelte
<!-- Modal with global overlay utility -->
<div class="modal-overlay" onclick={handleCancel}>
  <div class="modal-content" onclick={(e) => e.stopPropagation()}>
    <!-- Modal content here -->
  </div>
</div>
```

```css
/* frontend/static/style.css */
:root {
  --modal-backdrop: rgba(0, 0, 0, 0.4);
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: var(--modal-backdrop);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(2px);
}
```
