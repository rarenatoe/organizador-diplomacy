

## 1. Core Architecture

- **Backend Stack:** Python 3.13, uv, FastAPI, SQLAlchemy. NEVER use Flask or mix presentation logic in backend.
- **Frontend Stack:** Svelte 5, TypeScript, Vite. NEVER place business logic or data processing in frontend components.
- **File Limits:** Maintain 400-line soft limit. Extract sub-domains when exceeded. NEVER create monolithic files.

## 2. Language Boundaries

- **Internal Code:** English ONLY for Python/TS variables, types, function names, database schemas, endpoints. NEVER use Spanish like `let listaEspera = []`.
- **UI Text:** Spanish ONLY for HTML labels, user messages, button text, error messages. NEVER translate user-facing text like "Partida 1".
- **API Properties:** NEVER translate API-coupled data properties (e.g., `mesa.jugadores`, `juegos_este_ano`). This causes ripple effects.

## 3. Directory Layout

- **Backend Organization:**
  - `backend/api/routers/` - FastAPI endpoints
  - `backend/db/` - Models and connection management
  - `backend/crud/` - Modular data access
  - `backend/organizador/` - Algorithms
  - `backend/sync/` - Notion integration
- **Frontend Organization:** ALL frontend code in `frontend/src/`. NEVER scatter outside src directory.

## 4. Component Architecture

- **Semantic Props:** Prefer boolean props like `destructive={true}` over specialized variants like `variant="ghost-danger"`. NEVER create proliferating variants.
- **Action Bubbling:** Feature components MUST bubble destructive actions to central orchestrators via callback props. NEVER perform API side-effects in nested UI components.

## 5. Core Workflows & Business Logic

### Player Ingestion Flow

- **Entry Methods:** Users enter players via inline Autocomplete or bulk CSV import. NEVER bypass similarity checks.
- **Similarity Validation:** Unrecognized names MUST be intercepted via Notion similarity check and paused at `SyncResolutionModal`. NEVER allow unrecognized names to proceed without validation.

### History Lookup Flow

- **Traversal Order:** MUST use strict 4-tier traversal: `TimelineEdge` -> `SnapshotPlayer` -> `SnapshotHistory` JSON logs -> `NotionCache`. NEVER skip tiers or access out of sequence.

### Manual Save Philosophy

- **Dumb Save Principle:** Frontend is absolute source of truth for manual edits. NEVER let backend merge historical weights or apply smart corrections.
- **Backend Overwrites:** Backend strictly overwrites existing state. NEVER implement complex merge logic for manual edits.

### Draft Algorithm Pipeline

- **Sequential Execution:** Calculate Tickets -> Distribute to Tables -> Assign Countries -> Deduplicate Waitlist. NEVER skip phases or execute out of order.

## 1. Database Philosophy

- **Database System:** Use disposable local SQLite with `sqlite (stdlib)` via `aiosqlite`. NEVER use persistent or external database services.
- **Schema Management:** Define DB schema in code, re-create as needed. NEVER use Alembic migrations or separate schema files.
- **Type Safety:** Use explicit type annotations for all functions and Pydantic models for validation. NEVER use untyped signatures.

## 2. CRUD Architecture (Repository Pattern)

- **Domain Organization:** Use functional Repository Pattern grouped by domain in `backend/crud/` with separate modules (games, players, snapshots, chain). NEVER cram DB operations into single files.
- **Domain Separation:** Each CRUD module handles specific domain with focused responsibilities. NEVER create modules handling unrelated domains.
- **Async Consistency:** Follow consistent async patterns with proper session handling and type annotations. NEVER mix sync/async patterns.

## 3. Backend Coding Standards

- **Logging:** Use `from backend.core.logger import logger` with appropriate levels. Use `exc_info=True` for exceptions. NEVER use `print()` or `pprint()`.

## 4. Schema & Data Integrity

- **Universal IDs:** Use centralized `graph_nodes` table for universal IDs and cascading deletes. NEVER implement separate ID systems.
- **Immutable Snapshots:** Flow data through immutable snapshots connected by `timeline_edges` with explicit source IDs. NEVER create mutable data structures.

## 5. Business Logic Patterns

- **Country Assignment:** Implement algorithm preventing player repetition with conditional country shields. NEVER allow unrestricted repetition.
- **Two-Step API:** Enforce `/api/game/draft` (in-memory) followed by `/api/game/save` (persistence). NEVER write draft data directly to database.
- **Notion Caching:** Cache Notion data locally via `backend/sync/cache_daemon.py`. NEVER make direct API calls during user interactions.

## 6. API Endpoint Rules

- **Snapshot Save:** `/api/snapshot/save` MUST blindly trust frontend payload. NEVER merge historical weights or apply corrections.
- **Player Lookup:** `/api/player/lookup` MUST use 4-tier fallback: Timeline -> Global Snapshot -> JSON Logs -> Notion Cache. NEVER skip tiers.
- **Priority Field:** Treat `priority` as semantically boolean (strictly `0` or `1`). NEVER use non-boolean values.
- **Game Generation:** Execute two-phase algorithm: distribution loop first, country assignment second. NEVER interleave phases.
- **Hashing Keys:** ALWAYS hash by primitive attributes (`.name`) when using `Counter()` or dict keys. NEVER pass Pydantic models as keys.

## 1. Core Architecture & Organization

- **Tech Stack:** Svelte 5, TypeScript, Vite. Do not use alternative frameworks.
- **File Limits:** Maintain a 400-line soft limit per file. Extract sub-domains/components when exceeded.
- **Localization:** Route ALL UI translations through `frontend/src/i18n.ts`. No hardcoded strings.
- **Component Routing:** Categorize `frontend/src/components/` strictly by responsibility:
  - `ui/`: Atomic, domain-agnostic elements (Buttons, Badges).
  - `modals/`: Overlays and dialogs.
  - `layout/`: Structural containers.
  - `features/`: Domain-specific logic and complex views.
- **Logging:** Use `logger.info()`, `warn()`, and `error()` from `src/utils/logger.ts`. NEVER use `console.log()`.

## 2. Svelte 5 Reactivity & State

- **Runes:** Use `$state`, `$derived`, and `$effect`. Never use `let` for reactive variables.
- **Complex Derivations:** NEVER use nested ternary operators. For complex conditionals, use `$derived.by(() => { if (x) return y; return z; })`.
- **Context-Aware Components:** Prefer using `$derived` state (e.g., `isEditing = $derived(parentId !== null)`) to adapt a single component for Create/Edit views instead of duplicating the entire component file.
- **Global State:** Store global state in `stores.svelte.ts`. Use standard loading states: `-1` (unknown/loading) and `0` (loaded).

## 3. Component API Design

- **Separation of Concerns:** Keep Visual props (`variant`, `size`) strictly separate from Layout props (`fixedWidth`, `align`).
- **Domain-Agnostic Leaf Nodes:** Components in `ui/` MUST use semantic props (e.g., `variant="info"`). Never use domain terminology (e.g., `variant="gm"`).
- **Domain-Specific Nodes:** Components in `features/` MUST accept domain data explicitly (e.g., `gmName`, `players`).
- **Snippets over HTML:** Type snippets using `import type { Snippet } from "svelte"`. When passing dynamic rows to structural components (like `<DataTable>`), use Svelte 5 snippets instead of raw HTML `<tr>` elements to ensure safe DOM rendering.
- **Native Elements:** ALWAYS use the custom `<Button>` component instead of native `<button>`. Disabled buttons MUST include a `title` attribute for accessibility.

## 4. Styling & Design System (CRITICAL constraints)

- **NO Inline Styles:** Never use `style="..."` attributes. Always use semantic class names and Svelte's scoped `<style>` blocks.
- **Semantic Variables ONLY:** Never hardcode hex codes or raw palette colors (e.g., `var(--gray-50)`). Always map to semantic variables (e.g., `var(--bg-secondary)`, `var(--text-primary)`) to ensure flawless Dark Mode inversion.
- **Intents:**
  - **Solid Intents:** (`--primary-bg`) Use for high-emphasis elements. Always pair with white text.
  - **Subtle Intents:** (`--primary-bg-subtle`) Use for backgrounds/badges. Pair with tinted text (`--primary-text-subtle`).
- **Transparent Hovers:** Never use solid colors for hovering over transparent items. Use alpha overlays (`var(--overlay-hover)`, `var(--overlay-destructive)`).
- **Input Safety:** Text inputs must use the `.input-field` class. Focus states MUST use inset shadows (`box-shadow: inset 0 0 0 1px var(--border-focus)`) to prevent grid/table clipping.

## 5. CSS Compilation & Scope Overrides

- **Svelte CSS Pruning:** Svelte automatically strips "unused" CSS. If styling dynamic content, injected HTML, or elements passed via props (like standard `img` or `svg` icons), you MUST wrap the selector in `:global()` (e.g., `.btn-icon :global(svg)`).
- **Icon Contrast:** Apply `filter: brightness(0) invert(1);` to `:global(img)` and `:global(svg)` inside solid buttons to ensure contrast against dark backgrounds. Do not apply this to text/emojis.
- **Parent-to-Child Layout:** To pass custom spacing to a child, pass a `class` prop (e.g., `class="compact-title"`) and define `:global(.compact-title)` in the parent's style block. Do not build complex prop-based spacing systems.

## 6. Modals, Overlays & Data Flow

- **Modal Construction:** Use `.modal-overlay`, `var(--modal-backdrop)`, `z-index: 1000`, and `backdrop-filter: blur(2px)`.
- **Modal Events:** Always apply `onclick={onCancel}` to the overlay and `e.stopPropagation()` to the modal content window. Use standard callback props (`onCancel`, `onConfirm`).
- **Input Focus:** Use `use:autofocus` on the primary interaction element within a modal.
- **NO `window.prompt()`:** Completely banned. Always use proper modal dialogs and autocomplete components.
- **Data Ingestion:** Bulk data entry MUST NEVER write directly to state. Intercept via `/api/player/check-similarity` and pause with a resolution modal if conflicts exist. Inline player additions must use Autocomplete fetching from `/api/player/all`.

## 7. UI Design System & Layout (The Rule of 8)

- **Strict Rule of 8:** All paddings, margins, gaps, and dimensions must use absolute-reference variables (e.g., `var(--space-8)`, `var(--space-16)`). For non-standard multiples, strictly use explicit math: `calc(var(--space-8) * X)`. Never use "magic numbers" in pixels.
- **Intrinsic Sizing:** Components should not have fixed pixel `width` or `height`. Use padding, standard line-heights, and `max-width` to allow containers to wrap their contents naturally.
- **The Border Exemption:** Border widths are structural lines and are exempt from the Rule of 8. They must use standard `1px` or `2px` values, never a `--space-*` variable.
- **Flexbox Gap over Margins:** Leaf components (e.g., typography, buttons, badges) MUST NOT define their own external margins. Parent layouts must govern spacing exclusively using `display: flex; flex-direction: column; gap: var(--space-16);`. `margin-bottom` is reserved solely for spacing between major structural section wrappers.
- **Pure CSS State Management:** Never use inline JavaScript styles for complex UI states or dynamic colors. Pass primitive boolean props (e.g., `isActive={true}`) from parent to child, and toggle pure CSS classes (e.g., `.node.active`). Use CSS variables to handle internal color shifts.
- **Shorthand Padding:** Always optimize CSS padding (e.g., use `padding: var(--space-16);` instead of `padding: var(--space-16) var(--space-16);`).

## 8. UI Navigation & State Architecture (Svelte 5)

- **Avoid Flat State for Drill-downs:** Never use flat `$state` variables (e.g., `panelId`, `panelType`) to manage complex, multi-level UI navigation like side panels. This leads to hardcoded "Cancel/Back" logic.
- **The Navigation Stack Pattern:** Implement side-panel or modal drill-downs using an in-memory stack (array of objects) managed within a pure Svelte 5 `.svelte.ts` module. This allows generic, foolproof `pop()` and `push()` navigation where the UI always knows exactly where to return.
- **Encapsulate State:** Do not pollute layout components (like `App.svelte`) with business logic or router state. Extract this into singleton classes (e.g., `NavigationManager`) in `.svelte.ts` files.
- **Svelte 5 Snippets for Routing:** Avoid massive `{#if...} {:else if...}` blocks directly in your main HTML layout. If a component acts as a router rendering different child views, encapsulate that logic inside a `{#snippet panelRouter()}` block and invoke it declaratively with `{@render panelRouter()}` in the DOM.

## 1. Testing Execution

- **Frontend Tests:** ALWAYS use `bun run test` for Vitest suite. NEVER use `bun test` (incompatible with Vitest/Svelte 5).
- **Type Checking:** ALWAYS run `bun run typecheck` after directory restructuring or prop changes. NEVER skip after structural changes.
- **Backend Tests:** Use `uv run python -m pytest -q`. NEVER use alternative Python test runners.

## 2. Backend Testing Strategy

- **Framework:** Use pytest with `test_*.py` files co-located with implementation. NEVER separate test files or use incompatible frameworks.
- **Database:** Use in-memory SQLite (`:memory:`) exclusively. NEVER use persistent databases or external services.
- **Mocking:** Use `unittest.mock` for external dependencies, ALWAYS mock Notion API calls. NEVER hit real external APIs.
- **Test Structure:** Unit tests for pure functions, integration tests for database operations, end-to-end tests for API endpoints. NEVER mix types or miss integration coverage.

## 3. Frontend Testing Strategy

- **Framework:** Use Vitest with `@testing-library/svelte`. NEVER use incompatible frameworks.
- **Component Structure:** Unit tests for pure UI, integration tests for stateful components, accessibility tests for interactive elements. NEVER focus only on visual testing.
- **Query Selection:** Use `screen.getByRole('button', { name: /Text/i })` for buttons, `screen.getByLabelText()` or `screen.getByPlaceholderText()` for forms. NEVER use `getByText()` for emoji-separated buttons.
- **State Testing:** Use integration-style testing for `.svelte.ts` files with `$state` runes. NEVER use `vi.mock()` on these files.
- **Prop Testing:** Test visibility changes based on props (`editing`, `viewMode`, `hasPermission`). NEVER test only static states.
- **Factory Pattern:** Use fixtures in `frontend/src/tests/fixtures/` (e.g., `createMockPlayer()`). NEVER create giant inline JSON objects.
- **Helper Extraction:** Extract `render` calls and `waitFor` into shared helpers for complex components. NEVER duplicate render setup.

## 4. Frontend Test Maintenance

- **Snippet Testing:** Use `createRawSnippet` from `svelte` for snippet components. NEVER test without proper Svelte 5 snippet creation.
- **State Pre-population:** Use component props (`initialPlayers`) to pre-populate data. NEVER rely on fragile UI click-throughs.
- **DOM Query Updates:** Update queries immediately when CSS classes change or components are extracted. NEVER allow outdated selectors.
- **Validation:** Run `bun run typecheck` after CSS changes and verify visual regression after component extraction. NEVER skip validation steps.

## 5. General Test Editing & Maintenance

- **AST Integrity:** Use Nuclear Block Replacements (entire `describe`/`it` blocks). NEVER use loose line-deletion commands that break AST structure.

## 6. Test Quality Standards

- **Query Priority:** Use semantic HTML queries first, test user behavior over implementation details, assert accessible names over visual appearance. NEVER test implementation details or use fragile DOM traversal.
- **Mocking Strategy:** Mock external dependencies only, test real component interactions. NEVER over-mock that hides real bugs or mock internal logic.
- **Coverage Requirements:** Achieve 100% coverage for critical paths, ALWAYS test error handling, test edge cases with null/undefined inputs. NEVER skip error states or critical paths.

## 7. Frontend Structural Regression Guards

- **Assert DOM Layout Wrappers:** Because unit tests cannot test visual CSS rendering, you MUST explicitly test the structural HTML hierarchy. If a layout relies on a `.section` wrapper for Flexbox gaps, write an assertion to ensure that wrapper exists (`expect(container.querySelector('.section')).toBeInTheDocument();`).
- **Assert State Classes, Not Inline Styles:** Validate component states by asserting the presence of active CSS classes (e.g., `.active`, `.node-game`) rather than brittle inner HTML or inline style strings.
- **DRY UI Components:** When multiple views share a highly specific layout (e.g., timeline nodes), the UI must be extracted into a single source-of-truth component (e.g., `BaseNode`) to ensure test parity and visual consistency across the app.

## 8. State Module Testing (Svelte 5)

- **Pure Logic Testing:** Any logic extracted into a `.svelte.ts` file (using `$state`, `$derived`) must be tested entirely in isolation as pure TypeScript. Do not mount DOM elements or use component testing libraries to test these modules.
- **Singleton Resetting:** If testing a reactive singleton (e.g., a globally exported class instance), you MUST wipe its state in a `beforeEach()` block to prevent test pollution.
- **Test Real State, Not Simulations:** Component integration tests should not simulate logic via dummy variables (e.g., `let draftKey = 0; draftKey++;`). Instead, test how the component reacts to the actual imported state manager.
- **Verify Component Isolation:** When testing flows that require total UI resets (like opening a "New List" vs editing an existing one), verify that the state generator applies unique Svelte `{#key}` bindings to force true component destruction and recreation.

## Meta-Prompting & AI Communication

- **ABSOLUTE CONSTRAINTS ONLY:** When writing or updating rules, ALWAYS use absolute constraints (MUST, NEVER, BANNED, STRICTLY). NEVER use polite/emotional language ("Please", "Try to", "Avoid") as it dilutes token weights and probabilistic constraints.
- **LOGICAL GROUPING:** Group concepts with bullet points rather than repetitive "Rule / Anti-Pattern" boilerplate. Use clear headers and concise directives.
- **TOKEN EFFICIENCY:** Every word MUST serve a constraint purpose. Eliminate filler language and maximize information density.

## Rule Governance

- **Source of Truth:** Store AI rules in `docs/ai-rules/` directory. NEVER directly edit generated artifacts (`.clinerules`, `.windsurfrules`, `.github/copilot-instructions.md`).
- **Compilation:** ALWAYS run `bun run scripts/generate-ai-instructions.ts` after editing any markdown files in `docs/ai-rules/`. NEVER skip compilation as it causes inconsistencies across AI instruction files.

## Verification & Commits

- **Pre-Commit Validation:** ALWAYS validate with `bun run build && bun run lint && bun run typecheck`. NEVER commit without proper validation.
- **Local Syntax Checking:** ALWAYS check Svelte syntax problems locally. NEVER rely on CI/CD to catch syntax issues.
- **Commit Format:** Use conventional prefixes: `feat:`, `fix:`, `refactor:`, `test:`. NEVER use non-standard formats that break changelog generation.
