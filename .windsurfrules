

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
- `backend/db/`: Database models, views, and connection management.
- `backend/crud/`: Modular data access layer (Repository Pattern) with domain-specific modules.
- `backend/organizador/`: Core algorithms and pure data modeling.
- `backend/sync/`: Notion integration and caching daemon.
- `frontend/src/`: Svelte components, `$state` runes, API utilities, and types.

## Business Logic Patterns

**Semantic Modifiers** - Prefer semantic boolean props (e.g., `destructive={true}`) over specialized component variants (e.g., `variant="ghost-danger"`) to keep the design system clean and predictable.

## Interaction Patterns

**Action Bubbling** - Feature components should bubble up destructive actions (like deletions) to central orchestrators (`App.svelte`) via callback props. Avoid performing API side-effects inside deeply nested UI components to keep confirmation logic and state refreshes consistent.

## Database Philosophy

- **Disposable Local SQLite:** The database is local and disposable (`sqlite (stdlib)` via `aiosqlite`).
- **No Migrations:** DO NOT use Alembic migrations. The DB schema is defined in code and re-created as needed.
- **Strict Typing:** Use explicit type annotations for all function signatures. Use Pydantic models for request/response validation and TypedDicts where appropriate.

## CRUD Architecture (Repository Pattern)

- **Modular Data Access:** Never cram DB operations into a single file. Use a functional Repository Pattern grouped by domain inside `backend/crud/` (e.g., `games.py`, `players.py`, `snapshots.py`, `chain.py`).
- **Domain Separation:** Each CRUD module handles a specific domain (players, games, snapshots, timeline edges) with clear separation of concerns.
- **No God Files:** Strictly forbid the recreation of monolithic "God files" for database operations. Each module should be focused and maintainable.
- **Consistent Patterns:** All CRUD functions follow the same async patterns with proper session handling and type annotations.

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

## Testing Execution (STRICT ENFORCEMENT)

**FORBIDDEN COMMANDS:**

- **NEVER use `bun test`**: This uses Bun's native runner which is incompatible with our Vitest configuration and Svelte 5 runes.

**MANDATORY COMMANDS:**

- **ALWAYS use `bun run test`**: This triggers the Vitest suite specifically configured for this project.
- **Typing:** Run `bun run typecheck` after any directory restructuring or prop changes.

**BACKEND TESTING:**

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

**TESTING STATE RUNES**:

- **REGLA:** Exigir tests unitarios para verificar cambios de visibilidad o comportamiento en componentes que dependen de props de estado.
- **PROHIBITION:** NEVER use `vi.mock()` on `.svelte.ts` files or components using `$state`. You MUST use integration-style tests to verify actual reactive behavior.
- **VALIDATION STATES:** Test visibility changes based on props like `editing`, `viewMode`, `hasPermission`
- **EXAMPLE:** Test that `Button` shows/hides based on `visible={condition}` prop
- **EXAMPLE:** Test that `DataTable` switches between view/edit modes based on `editable` prop

**MOCKING DATA & TEST STRUCTURE (CRITICAL)**:

- **NEVER** use giant inline JSON objects for mock API responses, store states, or entity models.
- **ALWAYS** use the Factory Pattern via the `frontend/src/tests/fixtures/` directory (e.g., `createMockPlayer({ ...overrides })`).
- \*\*Only pass the exact properties relevant to the specific test as overrides to the factory. Let the factory handle the default noise/boilerplate.
- \*\*For complex components, ALWAYS extract the `render` call and loading state `waitFor` into a shared `renderMyComponent(propsOverrides)` helper at the top of the test file to eliminate boilerplate.

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
