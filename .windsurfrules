

## Core Architecture
- **Backend:** Pure Data & Algorithms. Python 3.13, uv, FastAPI, and SQLAlchemy. (No Flask).
- **Frontend:** Presentation & Translation. Svelte 5, TypeScript, Vite.
- **File Size:** 400-line soft limit per file. Extract sub-domains into new files unless they are highly cohesive indivisible units.

## The Spanglish Boundary
- **INTERNAL CODE:** Python/TS variables, types, function names, database schemas, and endpoints MUST be in English.
- **UI:** HTML text, labels, user-facing error messages, and test queries MUST be in Spanish.
- **Translation Layer:** Translations between internal code and UI must go through `frontend/src/i18n.ts`.

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

## Svelte 5 Runes & State

- **Reactivity:** Exclusively use `$state`, `$derived`, and `$effect`. Do not use `let` for variables that require reactivity but are not in `$state`.
- **Global Stores:** Found in `stores.svelte.ts`. UI components must use store getters directly in templates. No local copies of store state.
- **Loading States:** Use `-1` for unknown state; `0` when loaded.
- **Handlers & Bindings:** Use `onclick={() => ...}` syntax for events and `bind:value={var}` for bindings.

### Svelte 5 Snippets and CSS Scoping (CRITICAL)

- When a parent component passes HTML elements (like `<tr>` or `<td>`) into a child component via a `{#snippet}`, the child component's standard scoped CSS **will not affect those elements**.
- To style elements injected via snippets, the child component MUST use the `:global()` modifier (e.g., `:global(.table-wrap td) { ... }`). Failure to do this will result in stripped styles.

## Frontend Coding Standards

- **Logging Only:** NEVER use `console.log()` for any purpose. All debugging and error logging must use the custom logger from `src/utils/logger.ts` with appropriate methods (`logger.info()`, `logger.warn()`, `logger.error()`).

## UI Components & Styling

- **Buttons:** NEVER use native HTML `<button>` tags for actions. Always import and use the universal `<Button>` component (`import Button from './Button.svelte'`). Use orthogonal props to control appearance: `variant` ('primary', 'secondary', 'success', 'warning', 'ghost'), `size` ('md', 'sm'), `fill`, and `iconOnly`. Give disabled buttons a `title` attribute for user feedback.
- **Layouts:** Use the `<PanelLayout>` component with `{#snippet body()}`, `{#snippet header()}`, and `{#snippet footer()}` for side panel content.
- **CSS:** Use flex layout for panels. Strictly prefer **CSS Grid** (`display: grid`) over Flexbox when aligning lists with complex horizontal alignment (e.g., player tables, waiting lists). Use scoped `<style>` in components.
- **Domain-Agnostic UI:** Pure UI components (like Badges, Tooltips, Cards) MUST NOT contain domain-specific logic or nomenclature. Use semantic intent APIs (e.g., `variant="info" | "success" | "warning" | "error"`) instead of domain names (e.g., `variant="gm" | "veteran"`). The parent component is responsible for mapping domain data to semantic UI variants.

## CSS and Theming

- **No Hardcoded Hex Colors:** NEVER use hardcoded hex colors in `<style>` blocks for UI components. All colors must utilize global CSS variables defined in `frontend/static/style.css` (e.g., `var(--info-bg)`, `var(--tooltip-bg)`).
- **Inverted Floating Elements:** Tooltips, popovers, and toasts should use inverted color schemes (e.g., dark background with light text) for maximum Z-axis contrast.

## Component API

- **Explicit Layout Props:** Do not bundle layout behavior (like explicit widths for table column alignment) into visual shape props (like `pill`). Use explicit layout props (e.g., `fixedWidth: boolean`) so the consuming parent can decide if the component needs to hug its content or align to a grid.

## Domain Patterns

- **Constraint-Preserving UI (The Swap Pattern):** When manipulating strict arrays (like exactly 7 players per table), use the `SwapTarget` pattern. Users must click two entities to swap their positions to preserve mathematical constraints.
- **Handling Nulls:** Dropdowns interacting with optional backend data (e.g., `pais: null`) must explicitly handle nulls (e.g., `<option value={null}>🎲 Aleatorio</option>`).
- **Tooltips:** Avoid native `title="..."` attributes for complex information due to slow delay. Use custom CSS hover popovers (`.reason-tooltip` containing a `.tooltip-popover`).

## Execution Rules
- **CRITICAL:** NEVER use `bun test`. Always run tests using `bun run test`.
- **Backend:** Run using `uv run python -m pytest -q`.

## Backend Testing
- Use `pytest` for all backend tests. Test files should be `test_*.py` and co-located with their respective implementation files.
- Mock external dependencies (like Notion API) using `unittest.mock`.
- Test database operations exclusively using an in-memory SQLite database (`:memory:`).

## Frontend Testing
- **Framework:** Vitest + `@testing-library/svelte`.
- **State Mocking (CRITICAL OVERWRITE):** Do NOT use `vi.mock()` on `.svelte.ts` files that contain `$state` runes. State files must be tested using integration-style testing methodologies. 
- **DOM Accessibility:** Testing for buttons MUST use accessible queries (e.g., `screen.getByRole('button', { name: /Text/i })`). Do NOT use `getByText()` for buttons because emojis and text are structurally separated. For `iconOnly` buttons, rely on their `title` attribute, which `getByRole` uses as the accessible name.

## Rule Governance
- AI rules live in `docs/ai-rules/`. 
- NEVER directly edit `.clinerules`, `.windsurfrules`, or `.github/copilot-instructions.md`. They are generated artifacts.

## Verification & Commits
- Validate all tests and typing before committing: `bun run build && bun run lint && bun run typecheck`.
- Check for Svelte syntax problems locally.
- Git Commits must follow conventional prefixes: `feat:`, `fix:`, `refactor:`, `test:`.
