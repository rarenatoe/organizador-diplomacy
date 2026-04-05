---
id: frontend
title: Pillar 3 - Frontend & Svelte 5 Conventions
priority: 30
---

## Frontend Architecture (CRITICAL)

**TECH STACK**: Svelte 5, TypeScript, Vite
**FILE LIMIT**: 400 lines per file (extract sub-domains when exceeded)
**TRANSLATION**: All UI translations go through `frontend/src/i18n.ts`

## Component Design Principles

**LEAF COMPONENTS** (Domain-Agnostic):

- `Badge`, `Button`, `Tooltip`, `Input` - NO domain logic
- Use semantic APIs: `variant="info|success|warning|error"`
- NEVER use domain names: `variant="gm|veteran"`

**DOMAIN LAYOUT COMPONENTS** (Domain-Specific):

- `GameTableCard`, `PlayerList` - Accept domain data explicitly
- Use clear props: `gmName`, `tableNumber`, `players`
- AVOID over-abstracting with generic snippet APIs

## Svelte 5 Patterns (CRITICAL)

**REACTIVITY**:

- USE: `$state`, `$derived`, `$effect`
- AVOID: `let` for reactive variables

**SNIPPETS & CSS SCOPING** (CRITICAL):

- Parent → Child snippet injection: Child's scoped CSS **WILL NOT** affect snippet elements
- SOLUTION: Use `:global()` modifier: `:global(.table-wrap td) { ... }`
- FAILURE: Results in stripped styles and broken layouts

**STORES & STATE**:

- Global stores: `stores.svelte.ts`
- Loading states: `-1` (unknown), `0` (loaded)
- Event handlers: `onclick={() => ...}`
- Bindings: `bind:value={variable}`

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
- Update: `.mesa-card` → `.card` in all `.test.ts` files
