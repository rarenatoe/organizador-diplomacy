

## Core Architecture

- **Backend:** Pure Data & Algorithms. Python 3.13, uv, FastAPI, and SQLAlchemy. (No Flask).
- **Frontend:** Presentation & Translation. Svelte 5, TypeScript, Vite.
- **File Size:** 400-line soft limit per file. Extract sub-domains into new files unless they are highly cohesive indivisible units.

## The Spanglish Boundary (CRITICAL)

**INTERNAL CODE** (English ONLY):

- Python/TS variables, types, function names, database schemas, endpoints
- Component names, CSS classes, DOM variables
- Example: `let listaEspera = []` → `let waitingList = []`, `class="jugadores-excluidos"` → `class="excluded-players"`

**UI TEXT** (Spanish ONLY):

- HTML labels, user messages, button text, error messages
- Example: "Partida 1", "⚠️ Sin GM", "Copiar jugadores"

**CRITICAL EXCEPTION**: NEVER translate API-coupled data properties:

- `mesa.jugadores`, `juegos_este_ano`, `pais_reason`
- These map to frontend UI and database schema - translating causes massive ripple effects

## Directory Layout

- `backend/api/routers/`: FastAPI endpoints.
- `backend/db/`: Modular database operations (connection, crud, models, views).
- `backend/organizador/`: Core algorithms and pure data modeling.
- `backend/sync/`: Notion integration and caching daemon.
- `frontend/src/`: Svelte components, `$state` runes, API utilities, and types.

## Database Philosophy

- **Disposable Local SQLite:** The database is local and disposable (`sqlite (stdlib)` via `aiosqlite`).
- **No Migrations:** DO NOT use Alembic migrations. The DB schema is defined in code and re-created as needed.
- **Strict Typing:** Use explicit type annotations for all function signatures. Use Pydantic models for request/response validation and TypedDicts where appropriate.

## Backend Coding Standards

- **Logging Only:** NEVER use `print()` or `pprint()` for any purpose. All logging must use `from backend.core.logger import logger` with appropriate levels (`logger.info()`, `logger.warning()`, `logger.error(..., exc_info=True)` for exceptions).

## Schema & Data Integrity

- **Global IDs:** Use a centralized `graph_nodes` table for universal IDs and cascading deletes across all entities.
- **Snapshots & Events:** Data flows through immutable snapshots connected by events (`timeline_edges`). Snapshots require an explicit source ID.

## Business Logic Patterns

- **Shielding Strategy:** The country assignment algorithm (`organizador/core.py`) prevents player repetition by conditionally assigning countries to act as "shields" for other players.
- **Draft Mode:** A two-step API is strictly enforced. The `/api/game/draft` endpoint computes game tables in memory _without_ writing to the database, allowing manual review. Only `/api/game/save` persists the draft.
- **Notion Sync:** Notion data is cached locally. Background caching is orchestrated via `backend/sync/cache_daemon.py`.

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

## Modals & Overlays

**PATTERN:** All modals must use the global `.modal-overlay` utility class and `--modal-backdrop` variable defined in `style.css` for consistent visual behavior across the application.

**IMPLEMENTATION REQUIREMENTS:**

- **Backdrop:** Use `.modal-overlay` with `position: fixed`, `inset: 0`, `background: var(--modal-backdrop)`, `display: flex`, `align-items: center`, `justify-content: center`
- **Z-Index:** Use high `z-index` (1000+) to escape stacking contexts from parent panels like `SidePanel` (z-index: 50)
- **Backdrop Filter:** Apply `backdrop-filter: blur(2px)` for modern visual effects
- **Click Handling:** Implement click on overlay to close modal (`onclick={onCancel}`) and `e.stopPropagation()` on modal content to prevent event bubbling
- **Component Props:** Use clear props: `onImport: (text: string) => void`, `onCancel: () => void`
- **Autofocus:** Apply `autofocus` action to textarea for immediate user interaction

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

## Testing Execution (CRITICAL)

**COMMANDS**:

- NEVER: `bun test`
- ALWAYS: `bun run test`
- Backend: `uv run python -m pytest -q`

## Backend Testing Strategy

**FRAMEWORK**: pytest
**TEST FILES**: `test_*.py` (co-located with implementation)
**DATABASE**: In-memory SQLite (`:memory:`) only

**MOCKING**:

- External dependencies: Use `unittest.mock`
- Notion API: Always mock, never hit real API
- Database operations: Test with in-memory SQLite

**TEST STRUCTURE**:

- Unit tests for pure functions
- Integration tests for database operations
- End-to-end tests for API endpoints

## Frontend Testing Strategy

**FRAMEWORK**: Vitest + `@testing-library/svelte`

**COMPONENT TESTING**:

- Unit tests for pure UI components
- Integration tests for stateful components
- Accessibility tests for interactive elements

**DOM QUERY PATTERNS**:

- Buttons: `screen.getByRole('button', { name: /Text/i })`
- NEVER: `getByText()` for buttons (emojis separated from text)
- Icon-only: Use `title` attribute for accessible name
- Forms: `screen.getByLabelText()`, `screen.getByPlaceholderText()`

**STATE TESTING** (CRITICAL):

- NEVER: `vi.mock()` on `.svelte.ts` files with `$state` runes
- USE: Integration-style testing methodology
- REASON: State files require real reactivity for accurate testing

## Test Maintenance (CRITICAL)

**DOM QUERY UPDATES**:

- CSS class changes → IMMEDIATELY update test queries
- Component extraction → Update all affected selectors
- Search patterns: `querySelector`, `closest`, `getBy` calls

**SYNCHRONIZE DOM QUERIES**:

- Whenever you abstract HTML into components, rename CSS classes, or translate Spanglish classes to English, you MUST immediately update `querySelector`, `closest`, and `getBy` calls in the corresponding `.test.ts` files. Legacy integration tests are the first thing to break during CSS/DOM refactors.

**FAILURE PREVENTION**:

- Legacy integration tests fail without query updates
- Run `bun run typecheck` after CSS changes
- Verify visual regression after component extraction

## Test Quality Standards

**ASSERTION PATTERNS**:

- Use semantic HTML queries first
- Test user behavior, not implementation details
- Assert accessible names, not visual appearance

**MOCKING PRINCIPLES**:

- Mock external dependencies only
- Test real component interactions
- Avoid over-mocking that hides real bugs

**COVERAGE REQUIREMENTS**:

- Critical user paths: 100% coverage
- Error handling: Always test error states
- Edge cases: Test null/undefined inputs

## Rule Governance
- AI rules live in `docs/ai-rules/`. 
- NEVER directly edit `.clinerules`, `.windsurfrules`, or `.github/copilot-instructions.md`. They are generated artifacts.

## Verification & Commits
- Validate all tests and typing before committing: `bun run build && bun run lint && bun run typecheck`.
- Check for Svelte syntax problems locally.
- Git Commits must follow conventional prefixes: `feat:`, `fix:`, `refactor:`, `test:`.
