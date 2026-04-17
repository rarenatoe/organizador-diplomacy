

## 0. Domain Context (CRITICAL)

- **The Application:** This is a Diplomacy Tournament Organizer.
- **Core Entities:** - `Snapshots` (imported/synced player rosters).
  - `Games` (Generated tables consisting of exactly 7 players + optional Game Masters).
  - `Waitlists` (Players who did not get seated).
- **The Algorithm:** Prioritizes seating based on veteran status, games played this year, and historical country assignments to prevent repetition.

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

## 6. Data Modeling & API Boundaries

- **Immutable Identity (`notion_id` over `name`):** NEVER rely on user-editable strings for relational mapping or deduplication. ALWAYS anchor to an immutable external ID (`notion_id`).
- **Safe Legacy Migrations:** When introducing immutable IDs, write custom SQLAlchemy lifecycle hooks to auto-link existing records via heuristics BEFORE enforcing unique constraints.
- **Nested Objects over Flat Keys:** Group related data into nested objects (e.g., `country: { name, reason }`). Swapping an object reference automatically carries its related metadata, preventing orphaned data.
- **Strict API Purity:** The backend MUST NEVER send formatted UI strings (e.g., `etiqueta: "Antiguo (15 juegos)"`). APIs MUST send strictly typed, pure primitive data. The frontend is solely responsible for localization and UI formatting.
- **Synchronize Read & Write Models (CQRS):** When altering a database schema or write payload, you MUST simultaneously update the aggregate SQL views (e.g., `get_game_event_detail`) and their TypeScript interfaces.
- **Explicit Error Contracts:** The frontend API wrapper MUST explicitly handle framework-specific error shapes (like FastAPI's 422 `HTTPValidationError` array) and surface exact field-level rejections to the user.

## 7. State Management

### Svelte 5 State Patterns

- **Functional POJO State Modules:** Extract complex state into functional POJOs (Plain Old JavaScript Objects) using Svelte 5 runes (`$state`, `$derived`), NEVER ES6 Classes. This guarantees method purity and eases serialization.
- **Discriminated Union State Grouping:** Group related state variables (e.g., `isVisible`, `pendingData`, `resultsArray`) into a single Discriminated Union type (e.g., `type State = { status: 'idle' } | { status: 'resolving', data: X }`). This strictly eliminates impossible states.
- **Logic File Naming:** NEVER name a logic file identically to a UI file (e.g., avoid `Component.svelte` and `Component.svelte.ts`). Use `lowerCamelCaseState.svelte.ts` for the logic file to prevent bundler collisions.

### Type Architecture

- **Strict Type Safety:** Absolutely NO `any`, `unknown`, or dirty type casting (`as Type`) to bypass errors.
- **Component-Level Generics:** Use component-level Generics (`<script lang="ts" generics="T extends {...}">`) so components adapt safely to the data shapes passed to them.

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
- **Game Generation:** Execute two-phase algorithm: distribution loop first, country assignment second. NEVER interleave phases.
- **Hashing Keys:** ALWAYS hash by primitive attributes (`.name`) when using `Counter()` or dict keys. NEVER pass Pydantic models as keys.

## 7. Query Mechanics & Synchronization

- **The Cartesian Product Trap:** When optimizing SQLAlchemy queries by removing unused models from a `select()` list, NEVER remove the `.join()` clause if it restricts the relational mapping. Missing joins cause cross-join fan-outs that crash the frontend.
- **Unified Sync Pipeline:** Disparate logic for background daemons and manual API syncs causes race conditions. ALWAYS unify into a singular pipeline: Extraction (`fetch_notion_data`) -> Transformation (`build_notion_players_lookup`) -> Loading (`notion_cache_to_db`).
- **Granular Conflict Resolution:** Bulk data ingestion MUST intercept similarities and pause. Let the user decide the resolution strategy (`link_rename`, `link_only`, `use_existing`, `merge`). Blindly merging data destroys user intent.

## 1. Core Architecture & Svelte 5 Reactivity

- **Stack:** STRICTLY Svelte 5, TypeScript, Vite. NEVER use other frameworks.
- **Runes ONLY:** USE `$state`, `$derived`, `$effect`. NEVER use `let` for reactive state.
- **Derived State:** USE `$derived.by(() => {...})` for complex logic. NEVER use nested ternaries.
- **Context Adaptation:** USE `$derived` (e.g., `isEditing = $derived(id !== null)`) to adapt a single component for Create/Edit views.
- **Component Routing:** Categorize strictly. `ui/` MUST be domain-agnostic (e.g., `variant="danger"`). `features/` MUST be domain-aware (e.g., `player={player}`).
- **Logging:** ALWAYS use `logger.info()`, `warn()`, and `error()` from `src/utils/logger.ts`. NEVER use `console.log()`.

## 2. Layout, CSS Grid & The Rule of 8

- **Strict Rule of 8:** ALL paddings, margins, gaps, and dimensions MUST use absolute-reference variables (`var(--space-8)`). For non-standard multiples, use `calc(var(--space-8) * X)`. Border widths (`1px`) are the ONLY exception.
- **The Border Exemption:** Border widths (`1px` or `2px`) are structural lines and are EXEMPT from the Rule of 8.
- **Svelte CSS Pruning:** Svelte strips "unused" CSS. WHEN styling dynamic content, injected HTML, or standard `<svg>` elements, you MUST wrap the selector in `:global()` (e.g., `.btn-icon :global(svg)`).
- **Icon Contrast:** ALWAYS apply `filter: brightness(0) invert(1);` to `:global(img)` and `:global(svg)` inside solid primary buttons to ensure contrast against dark backgrounds.
- **The Flexbox-in-Grid Blowout:** When nesting a `display: flex` container inside a CSS Grid column, flex items default to `min-width: auto` and blow out `minmax()` constraints. ALWAYS apply `min-width: 0` to both the flex container and its flex children.
- **Ghost Cells for Tabular Grids:** NEVER conditionally omit structural grid cells. If data is null, omit the content but render the empty wrapper `div` cell to prevent trailing elements from sliding into the wrong columns.
- **Zero Layout Shift:** When toggling a component between an editable state (`<input>`) and a read-only state (`<span>`), the read-only element MUST mimic the exact padding, height, and margins of the input field.
- **Intrinsic Sizing:** Components MUST NOT have fixed pixel `width` or `height`. Use padding, standard line-heights, and `max-width` to allow containers to wrap their contents naturally.
- **Flexbox Gap over Margins:** Leaf components (typography, buttons, badges) MUST NOT define their own external margins. Parent layouts must govern spacing exclusively using `display: flex; gap: var(--space-X);`.

## 3. UI Design System & Component API

- **Pure CSS ONLY:** NEVER use Tailwind or utility classes. NEVER use `style="..."`. Wrap dynamic DOM target selectors in `:global()` (e.g., `:global(svg)`).
- **Semantic Variables:** ALWAYS map colors to semantic variables (e.g., `var(--bg-secondary)`). NEVER hardcode hex codes to guarantee Dark Mode inversion.
- **Reference Swapping over Mutation:** When exchanging complex nested objects between UI elements, swap the entire object reference. NEVER manually overwrite individual properties, as this silently destroys auxiliary metadata (like tooltips).
- **Snippets over HTML:** USE `import type { Snippet }` and Svelte snippets instead of raw HTML strings for dynamic rendering.

## 4. Product UX & Signal-to-Noise

- **Gestalt Proximity (Wrapper Tooltips):** Do not force standalone icons (`ℹ️`) next to elements if the data relates directly to the element. `<Tooltip>` components MUST accept Svelte Snippets (`children`) to invisibly wrap components, turning the element itself into the hover surface.
- **Zero-Delay Data Discovery:** NEVER rely on the native HTML `title` attribute for critical data discovery (it has an OS-forced 500ms delay). ALWAYS use custom JS/Svelte popover components.
- **Contextual Metadata:** Hide administrative metadata (like Notion link indicators) in read-only domain summaries. Expose props (e.g., `showNotionIndicator={false}`) to keep layouts focused on domain output.
- **Concise Badges:** Keep badge text categorical (`False`). Push verbose supplementary data (`"15 juegos"`) into Wrapper Tooltips.

## 5. State & Data Flow

- **The Navigation Stack Pattern:** USE an in-memory stack (array in `.svelte.ts`) for multi-level navigation. NEVER use flat variables (`$state(panelId)`), as this leads to hardcoded "Back" logic.
- **Modals:** USE `.modal-overlay`, `var(--modal-backdrop)`. ALWAYS apply `onclick={onCancel}` to overlay and `e.stopPropagation()` to content.
- **Input Focus:** ALWAYS use `use:autofocus` on the primary interaction element within a modal or panel.
- **Banned Browser APIs:** NEVER use `window.prompt()`, `window.alert()`, or `window.confirm()`. ALWAYS use proper custom modal components.
- **Encapsulate State:** Do not pollute layout components (`App.svelte`) with business logic. Extract complex state into singleton classes in `.svelte.ts` files.
- **Data Ingestion:** Bulk data entry MUST NEVER write directly to state. Intercept via `/api/player/check-similarity` and present `SyncResolutionModal` if conflicts exist.

## 6. Defensive UI & Layout

- **Floating UI Guard:** Do not base the visibility of floating elements (dropdowns, modals) solely on derived array lengths or data states. ALWAYS pair visibility with an explicit user-interaction boolean (e.g., `isActive` triggered by `onfocus` or `oninput`) to prevent background state syncs from creating zombie UI elements.
- **Pre-Flight Validations:** ALWAYS validate operations against local, synchronous state before firing async API calls or opening resolution modals.

## 7. CSS & Styling Constraints

- **Class Injection:** NEVER use raw string concatenation for dynamic classes (e.g., `class="{base} {active ? 'active' : ''}"`). ALWAYS use a dedicated utility like `cx()` or `clsx` to prevent `undefined` or `false` from bleeding into the DOM.
- **Structural vs. Visual:** STRICTLY separate structural layout classes (`wrapperClass`) from visual/text classes (`class`). NEVER apply `display: flex` to shared text-formatting classes, as it breaks truncation (`text-overflow: ellipsis`).
- **Flexbox Inputs:** HTML `<input>` elements have a browser-default intrinsic width. When placing them inside a `flex` container, you MUST apply `min-width: 0` to the input, otherwise it will refuse to shrink and blow out the grid layout.
- **Sticky Stacking Contexts:** Elements inside a `position: sticky` table cell are trapped in its stacking context. To make an absolute child (like a dropdown) overlap the next table row, you MUST elevate the parent cell itself (e.g., `td.sticky-col:focus-within { z-index: 50; }`).

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

## 9. Test Maintenance & Resilience

- **Kill Zombie Tests:** If you fix the architectural root cause of a bug (e.g., introducing `notion_id`), aggressively HUNT DOWN and DELETE tests written specifically to verify the old, hacky workarounds (e.g., `GROUP BY max()` deduplication queries).
- **Scope DOM Selectors:** When testing UI interactions, ALWAYS scope DOM selectors to their specific domain context (e.g., `document.querySelectorAll('.country-cell .tooltip-trigger')`) to prevent test breakage as the design system expands.

## 10. Test Suite Optimization

- **The Fixture Rule:** Test files MUST remain hyper-focused on assertions. Any mock data array, object, or `defaultProps` setup exceeding 10 lines MUST be extracted to a sibling `*.fixtures.ts` file.
- **The Render Wrapper Standard:** NEVER repeat `render(Component, { props: {...} })` across multiple test cases. Every test file MUST implement a centralized `renderComponent(overrides = {})` factory function to keep component mounting DRY and reduce visual noise.

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

## AI Prompt Engineering & Constraint Management

- **Atomize Prompts:** When fixing cascading architectural changes, break instructions down into atomized, file-specific prompts. Monolithic prompts cause agents to gloss over critical lines of code.
- **Absolute Constraints:** ALWAYS use absolute constraints ("MUST", "NEVER", "ALWAYS"). Do not use "prefer" or "avoid" to prevent LLM hallucinations.
