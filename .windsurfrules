

## Core Architecture

**Rule:** Backend serves as pure data and algorithms using Python 3.13, uv, FastAPI, and SQLAlchemy.
**Anti-Pattern:** Using Flask or mixing presentation logic in backend code.

**Rule:** Frontend handles presentation and translation using Svelte 5, TypeScript, and Vite.
**Anti-Pattern:** Placing business logic or data processing in frontend components.

**Rule:** Maintain 400-line soft limit per file by extracting sub-domains into separate files.
**Anti-Pattern:** Creating monolithic files with multiple responsibilities unless highly cohesive and indivisible.

## Language Boundaries

**Rule:** Use English exclusively for internal code including Python/TS variables, types, function names, database schemas, and endpoints.
**Anti-Pattern:** Using Spanish for variable names like `let listaEspera = []` instead of `let waitingList = []`.

**Rule:** Use Spanish exclusively for UI text including HTML labels, user messages, button text, and error messages.
**Anti-Pattern:** Translating user-facing text like "Partida 1" or "Copiar jugadores" to English.

**Rule:** Never translate API-coupled data properties that map between frontend UI and database schema.
**Anti-Pattern:** Translating properties like `mesa.jugadores`, `juegos_este_ano`, or `pais_reason` which causes ripple effects.

## Directory Layout

**Rule:** Organize backend with `backend/api/routers/` for FastAPI endpoints, `backend/db/` for models and connection management, `backend/crud/` for modular data access, `backend/organizador/` for algorithms, and `backend/sync/` for Notion integration.
**Anti-Pattern:** Mixing concerns across directories or creating god files.

**Rule:** Place all frontend code in `frontend/src/` with Svelte components, `$state` runes, API utilities, and types.
**Anti-Pattern:** Scattering frontend code outside the designated src directory.

## Component Architecture

**Rule:** Prefer semantic boolean props like `destructive={true}` over specialized component variants like `variant="ghost-danger"`.
**Anti-Pattern:** Creating proliferating component variants that complicate the design system.

**Rule:** Feature components should bubble up destructive actions to central orchestrators via callback props.
**Anti-Pattern:** Performing API side-effects inside deeply nested UI components.

## Core Workflows & Business Logic

### Player Ingestion Flow

**Rule:** Users enter players via inline Autocomplete or bulk CSV import.
**Anti-Pattern:** Bypassing the similarity check for unrecognized names.

**Rule:** Unrecognized names MUST be intercepted via Notion similarity check and paused at the `SyncResolutionModal`.
**Anti-Pattern:** Allowing unrecognized names to proceed without similarity validation.

### History Lookup Flow

**Rule:** Must use strict 4-tier traversal: `TimelineEdge` -> `SnapshotPlayer` -> `SnapshotHistory` JSON logs -> `NotionCache`.
**Anti-Pattern:** Skipping traversal tiers or accessing data out of sequence.

### Manual Save Philosophy

**Rule:** Implement "Dumb Save" where frontend is the absolute source of truth for manual edits.
**Anti-Pattern:** Backend attempting to merge historical weights or applying smart corrections.

**Rule:** Backend strictly overwrites existing state without attempting to merge historical weights.
**Anti-Pattern:** Backend implementing complex merge logic for manual edits.

### Draft Algorithm Pipeline

**Rule:** Execute sequential phases: Calculate Tickets -> Distribute to Tables -> Assign Countries -> Deduplicate Waitlist.
**Anti-Pattern:** Skipping pipeline phases or executing them out of order.

## Database Philosophy

**Rule:** Use disposable local SQLite database with `sqlite (stdlib)` via `aiosqlite`.
**Anti-Pattern:** Using persistent database systems or external database services.

**Rule:** Define DB schema in code and re-create as needed without Alembic migrations.
**Anti-Pattern:** Using database migration tools or maintaining separate schema files.

**Rule:** Use explicit type annotations for all function signatures and Pydantic models for request/response validation.
**Anti-Pattern:** Using untyped function signatures or skipping validation models.

## CRUD Architecture (Repository Pattern)

**Rule:** Use functional Repository Pattern grouped by domain inside `backend/crud/` with separate modules for games, players, snapshots, and chain.
**Anti-Pattern:** Cramming DB operations into a single file or creating monolithic database modules.

**Rule:** Maintain clear domain separation where each CRUD module handles a specific domain with focused responsibilities.
**Anti-Pattern:** Creating modules that handle multiple unrelated domains or concerns.

**Rule:** Follow consistent async patterns with proper session handling and type annotations across all CRUD functions.
**Anti-Pattern:** Mixing sync/async patterns or inconsistent session management.

## Backend Coding Standards

**Rule:** Use `from backend.core.logger import logger` with appropriate levels for all logging (`logger.info()`, `logger.warning()`, `logger.error(..., exc_info=True)` for exceptions).
**Anti-Pattern:** Using `print()` or `pprint()` for any logging or debugging purposes.

## Schema & Data Integrity

**Rule:** Use centralized `graph_nodes` table for universal IDs and cascading deletes across all entities.
**Anti-Pattern:** Implementing separate ID systems or manual cascading logic.

**Rule:** Flow data through immutable snapshots connected by events (`timeline_edges`) with explicit source IDs.
**Anti-Pattern:** Creating mutable data structures or snapshots without proper source tracking.

## Business Logic Patterns

**Rule:** Implement country assignment algorithm that prevents player repetition by conditionally assigning countries as shields.
**Anti-Pattern:** Allowing unrestricted player repetition or missing shield assignments.

**Rule:** Enforce two-step API with `/api/game/draft` computing tables in memory without database writes, followed by `/api/game/save` for persistence.
**Anti-Pattern:** Writing draft data directly to database or skipping the review step.

**Rule:** Cache Notion data locally with background orchestration via `backend/sync/cache_daemon.py`.
**Anti-Pattern:** Making direct API calls to Notion during user interactions.

## API Endpoint Rules

**Rule:** The `/api/snapshot/save` endpoint must blindly and strictly trust the frontend payload without historical overrides.
**Anti-Pattern:** Backend attempting to merge historical weights or apply smart corrections during save operations.

**Rule:** Lookups via `/api/player/lookup` must use deep 4-tier fallback: Timeline -> Global Snapshot -> JSON Logs -> Notion Cache.
**Anti-Pattern:** Skipping traversal tiers or accessing data out of sequence during lookups.

**Rule:** Treat the `priority` field as semantically boolean, using strictly `0` or `1` in logic and test setups.
**Anti-Pattern:** Using non-boolean values for priority fields or treating them as integers.

**Rule:** Execute game generation with two-phase algorithm: distribution loop to group players first, then assign countries second.
**Anti-Pattern:** Interleaving distribution and country assignment or skipping the grouping phase.

**Rule:** Always hash by primitive attributes (e.g., `.name`) when using `Counter()` or dict keys.
**Anti-Pattern:** Passing Pydantic models like `DraftPlayer` into `Counter()` or using them as dict keys.

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

## CSS & Design System Guidelines

When styling components or adding new UI features, strictly adhere to the following semantic design system rules:

1. **Never Hardcode Colors in Components:** Do NOT use hex codes (e.g., `#ffffff`) or raw palette variables (e.g., `var(--gray-50)`) directly in component styles. Always map to semantic relational variables (e.g., `var(--bg-secondary)`, `var(--text-primary)`). This guarantees flawless Dark Mode inversion.

2. **Solid vs. Subtle Intents:**
   - Use **Solid** intents (`--primary-bg`, `--danger-bg`) ONLY for high-emphasis actions like Primary Buttons. Solid intents use white text (`--primary-text`).
   - Use **Subtle** intents (`--primary-bg-subtle`, `--warning-bg-subtle`) for backgrounds, badges, inactive nodes, and alerts. Subtle intents use dark/tinted text (`--primary-text-subtle`).

3. **Ghost & Transparent Hovers:** Never use solid colors for hovering over transparent elements (like Ghost buttons or list items). Always use the mathematical alpha overlays (`var(--overlay-hover)`, `var(--overlay-destructive)`). This ensures the hover state beautifully tints whatever background it sits on.

4. **Form Element Safety:**
   - Always use `class="input-field"` for text inputs to ensure consistent padding, typography, and dark-mode inheritance.
   - When defining focus rings (e.g., `:focus`), always use an `inset` box-shadow (`box-shadow: inset 0 0 0 1px var(--border-focus)`). This prevents the focus ring from being clipped when the input is placed inside strict CSS Grids or Table cells.

5. **Icon Contrast in Buttons:** Icons (SVGs/IMGs) inside Solid buttons (Primary, Success, Danger) must use CSS filters (`filter: brightness(0) invert(1);`) to force them to be pure white, ensuring contrast against the solid background.

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

## Testing Execution

**Rule:** Always use `bun run test` to trigger the Vitest suite specifically configured for this project.
**Anti-Pattern:** Using `bun test` which is incompatible with Vitest configuration and Svelte 5 runes.

**Rule:** Run `bun run typecheck` after any directory restructuring or prop changes.
**Anti-Pattern:** Skipping type checking after structural changes that may break imports.

**Rule:** Use `uv run python -m pytest -q` for backend testing.
**Anti-Pattern:** Using alternative Python test runners or incorrect pytest configurations.

## Backend Testing Strategy

**Rule:** Use pytest framework with `test_*.py` files co-located with implementation.
**Anti-Pattern:** Separating test files from implementation or using incompatible test frameworks.

**Rule:** Use in-memory SQLite (`:memory:`) exclusively for database testing.
**Anti-Pattern:** Using persistent databases or external database services in tests.

**Rule:** Use `unittest.mock` for external dependencies and always mock Notion API calls.
**Anti-Pattern:** Hitting real external APIs or using inadequate mocking strategies.

**Rule:** Structure tests with unit tests for pure functions, integration tests for database operations, and end-to-end tests for API endpoints.
**Anti-Pattern:** Mixing test types or missing critical integration coverage.

## Frontend Testing Strategy

**Rule:** Use Vitest with `@testing-library/svelte` for frontend testing.
**Anti-Pattern:** Using incompatible testing frameworks or libraries.

**Rule:** Structure component tests with unit tests for pure UI components, integration tests for stateful components, and accessibility tests for interactive elements.
**Anti-Pattern:** Focusing only on visual testing without interaction or accessibility coverage.

**Rule:** Use `screen.getByRole('button', { name: /Text/i })` for buttons and `screen.getByLabelText()` or `screen.getByPlaceholderText()` for forms.
**Anti-Pattern:** Using `getByText()` for buttons with emojis separated from text or inappropriate query selectors.

**Rule:** Use integration-style testing methodology for `.svelte.ts` files with `$state` runes; never use `vi.mock()` on these files.
**Anti-Pattern:** Mocking state files or components that require real reactivity for accurate testing.

**Rule:** Test visibility changes based on props like `editing`, `viewMode`, `hasPermission` and verify component behavior based on conditional props.
**Anti-Pattern:** Testing only static states without verifying reactive behavior or prop-driven changes.

**Rule:** Use Factory Pattern via `frontend/src/tests/fixtures/` directory (e.g., `createMockPlayer({ ...overrides })`) instead of giant inline JSON objects.
**Anti-Pattern:** Creating large inline mock objects or duplicating boilerplate across tests.

**Rule:** Extract `render` calls and loading state `waitFor` into shared `renderMyComponent(propsOverrides)` helpers for complex components.
**Anti-Pattern:** Duplicating render setup code and boilerplate in multiple test cases.

### Frontend Test Maintenance

**Rule:** When testing components that accept snippets, use `createRawSnippet` from `svelte` to programmatically forge valid snippets.
**Anti-Pattern:** Attempting to test snippet functionality without proper Svelte 5 snippet creation.

**Rule:** Use component props (e.g., `initialPlayers`) to pre-populate data before asserting behaviors instead of fragile UI click-throughs.
**Anti-Pattern:** Relying on complex UI interaction sequences to set up initial test state.

**Rule:** Update DOM queries immediately when CSS classes change, components are extracted, or selectors are renamed.
**Anti-Pattern:** Allowing outdated selectors to persist after DOM structure changes.

**Rule:** Update `querySelector`, `closest`, and `getBy` calls immediately when HTML is abstracted into components or CSS classes are renamed.
**Anti-Pattern:** Neglecting test updates during CSS/DOM refactors that break integration tests.

**Rule:** Run `bun run typecheck` after CSS changes and verify visual regression after component extraction.
**Anti-Pattern:** Skipping validation steps that can catch breaking changes early.

## General Test Editing & Maintenance

**Rule:** Use Nuclear Block Replacements (replacing entire `describe` or `it` blocks) to guarantee Abstract Syntax Tree (AST) integrity in test files.
**Anti-Pattern:** Using loose line-deletion commands that can break AST structure and test file syntax.

## Test Quality Standards

**Rule:** Use semantic HTML queries first, test user behavior rather than implementation details, and assert accessible names rather than visual appearance.
**Anti-Pattern:** Testing implementation details, visual appearance, or using fragile DOM traversal.

**Rule:** Mock external dependencies only, test real component interactions, and avoid over-mocking that hides real bugs.
**Anti-Pattern:** Mocking internal component logic or creating mocks that prevent testing of actual behavior.

**Rule:** Achieve 100% coverage for critical user paths, always test error handling, and test edge cases with null/undefined inputs.
**Anti-Pattern:** Skipping error states, edge cases, or critical user interaction paths.

## Rule Governance

**Rule:** Store AI rules in `docs/ai-rules/` directory as the source of truth.
**Anti-Pattern:** Directly editing `.clinerules`, `.windsurfrules`, or `.github/copilot-instructions.md` which are generated artifacts.

**Rule:** Run `bun run scripts/generate-ai-instructions.ts` after editing any markdown files in `docs/ai-rules/` to compile rules into root directory AI files.
**Anti-Pattern:** Editing AI rule files without running the compilation script, causing inconsistencies across AI instruction files.

## Verification & Commits

**Rule:** Validate all tests and typing before committing using `bun run build && bun run lint && bun run typecheck`.
**Anti-Pattern:** Committing changes without proper validation that may break the build or introduce errors.

**Rule:** Check for Svelte syntax problems locally before pushing changes.
**Anti-Pattern:** Relying on CI/CD to catch syntax issues that should be identified during development.

**Rule:** Use conventional commit prefixes: `feat:`, `fix:`, `refactor:`, `test:`.
**Anti-Pattern:** Using non-standard commit message formats that break automated changelog generation.
