

## 1. Domain Context (CRITICAL)

- **The Application:** Diplomacy Tournament Organizer.
- **Core Entities:** `Snapshots` (player rosters), `Games` (7-player tables + GMs), `Waitlists` (unseated players).
- **The Algorithm:** Prioritizes seating based on veteran status, games played this year, and historical country assignments to prevent repetition.

## 2. Global Architecture & Boundaries

- **Backend Stack:** Python 3.13, uv, FastAPI, SQLAlchemy. NEVER use Flask or mix presentation logic in backend.
- **Frontend Stack:** Svelte 5, TypeScript, Vite. NEVER place business logic or data processing in frontend components.
- **Language Boundaries:** - Internal Code: English ONLY (variables, types, DB schemas, endpoints). NEVER use Spanish (e.g., `listaEspera`).
  - UI Text: Spanish ONLY (HTML labels, buttons, error messages). NEVER translate user-facing text.
  - API Properties: NEVER translate API-coupled data properties (e.g., `mesa.jugadores`).

## 3. Directory Layout

- **Backend (`backend/`):** `api/routers/` (Endpoints), `db/` (Models), `crud/` (Data access), `organizador/` (Algorithms), `sync/` (Notion integration).
- **Frontend (`frontend/src/`):** ALL frontend code lives here. NEVER scatter outside.

## 4. Core Workflows

- **Player Ingestion:** Users enter players via Autocomplete or bulk CSV. Unrecognized names MUST be intercepted via Notion similarity check (`SyncResolutionModal`). NEVER bypass validations.
- **History Lookup:** MUST use strict 4-tier traversal: `TimelineEdge` -> `SnapshotPlayer` -> `SnapshotHistory JSON` -> `NotionCache`. NEVER skip tiers.
- **Manual Save (Dumb Save):** Frontend is absolute source of truth for manual edits. Backend strictly overwrites existing state. NEVER merge historical weights or apply smart corrections on manual saves.
- **Draft Pipeline:** Calculate Tickets -> Distribute to Tables -> Assign Countries -> Deduplicate Waitlist. NEVER skip phases or execute out of order.

## 1. Database & Schema

- **Database System:** Use disposable local SQLite (`aiosqlite`). NEVER use persistent external DBs or Alembic migrations. Define schema strictly in code.
- **Universal IDs:** Use centralized `graph_nodes` table for universal IDs and cascading deletes. NEVER implement separate ID systems.
- **Immutable Identity:** ALWAYS anchor to immutable external IDs (`notion_id`). NEVER rely on user-editable strings (`name`) for relational mapping.
- **Immutable Snapshots:** Flow data through immutable snapshots connected by `timeline_edges`. NEVER create mutable historical data structures.

## 2. API & Logic Boundaries

- **Repository Pattern:** Group CRUD operations by domain (`backend/crud/`). NEVER cram operations into single files or mix domains.
- **Strict API Purity:** Backend MUST NEVER send formatted UI strings (e.g., `"Antiguo (15 juegos)"`). APIs MUST send strictly typed primitive data.
- **Synchronized CQRS:** When altering a schema or write payload, you MUST simultaneously update aggregate SQL views and their TS interfaces.
- **Two-Step Generation:** Enforce `/api/game/draft` (in-memory) followed by `/api/game/save` (persistence). NEVER write draft data directly to DB.

## 3. Performance & SQLAlchemy "Fat Trimming"

- **Explicit Selection:** Fetch ONLY required columns (`select(NotionCache.notion_id, NotionCache.name)`). NEVER fetch entire models (`select(NotionCache)`) for read-only algorithms.
- **The Cartesian Trap:** When optimizing queries, NEVER remove `.join()` clauses if they restrict relational mapping. Missing joins cause cross-join fan-outs.
- **Type-Safe Mapping:** Explicitly map SQLAlchemy `Row` objects into typed dicts (`{"name": row.name}`). Avoid `**row.mappings()` to guarantee Pyright compile-time safety.

## 4. Python Typing & ISP

- **Minimal TypedDicts (ISP):** Pure functions MUST declare a minimal `TypedDict` representing exactly what they need, rather than demanding massive DB models.
- **Covariant Hints:** Use `collections.abc.Mapping` and `Sequence` in type hints so functions accept both slim and ORM-derived dicts.
- **Hashing Keys:** ALWAYS hash by primitive attributes (`.name`). NEVER pass Pydantic models as dict/Counter keys.

## 5. Coding Standards & Logging

- **Logging:** ALWAYS use `from backend.core.logger import logger` with appropriate levels. Use `exc_info=True` for exceptions. NEVER use `print()` or `pprint()`.

## 1. Svelte 5 Reactivity & State

- **Runes ONLY:** USE `$state`, `$derived`, `$effect`. NEVER use `let` for reactive state. Use `$derived.by()` for complex logic.
- **Functional POJO State:** Extract complex state into plain objects using Runes, NEVER ES6 Classes.
- **Discriminated Unions:** Group related state variables (e.g., `status: 'idle' | 'resolving'`) into Discriminated Unions to eliminate impossible states.
- **Navigation Stack:** USE an in-memory stack (array) for multi-level navigation. NEVER use flat variables (`$state(panelId)`).
- **Logic File Naming:** NEVER name a logic file identically to a UI file (e.g., avoid `Component.svelte` and `Component.svelte.ts`). Use `lowerCamelCaseState.svelte.ts` to prevent bundler collisions.
- **Component-Level Generics:** Use component-level Generics (`<script lang="ts" generics="T extends {...}">`) so components adapt safely to diverse data shapes.

## 2. Auto-Generated API SDK (CRITICAL)

- **NO MANUAL FETCHING:** NEVER write manual `fetch` calls or custom interfaces. ALWAYS use the `@hey-api` generated endpoints (e.g., `apiPlayerCheckSimilarity`) and types from `frontend/src/generated-api`.
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

## 1. Execution & Strategy

- **Runners:** Frontend: `bun run test` (Vitest). Backend: `uv run python -m pytest -q`.
- **Backend Mocking:** Use `unittest.mock` for external dependencies (e.g., Notion API). Use `:memory:` SQLite. NEVER hit real external APIs.
- **Frontend Querying:** Use semantic queries (`getByRole`, `getByPlaceholderText`). NEVER test implementation details or use fragile DOM traversal.

## 2. Svelte & DOM Testing Rules

- **State Module Testing:** Logic extracted to `.svelte.ts` files MUST be tested in isolation as pure TypeScript. NEVER use DOM mounting for pure logic.
- **Singleton Resetting:** ALWAYS wipe globally exported class/state instances in `beforeEach()` to prevent test pollution.
- **Structural Regression Guards:** Explicitly test HTML hierarchy. If a layout relies on a `.section` wrapper for gaps, assert its existence (`expect(container.querySelector('.section')).toBeInTheDocument();`).
- **DRY Renders & Fixtures:** Extensively mock data MUST live in `*.fixtures.ts`. EVERY test file MUST implement a centralized `renderComponent(overrides = {})` factory.
- **Snippet Testing:** Use `createRawSnippet` from `svelte` for snippet components. NEVER test without proper Svelte 5 snippet creation.

## 3. Auto-Generated SDK Testing Patterns (CRITICAL)

- **The Barrel File Trap:** Vite module resolution bypasses `vi.mock` for auto-generated `index.ts` files.
  - _Correct:_ `import * as api from "../../generated-api"; vi.spyOn(api, "apiPlayerGetAll").mockResolvedValue(...)`
  - _Incorrect:_ `vi.mock("../../generated-api", () => ...)`
- **Healthy Default Mocks:** Svelte `onMount` blocks will instantly crash if an API returns `undefined`. ALWAYS provide default `mockResolvedValue` spies in `beforeEach()`.
- **Mocking `@hey-api` Responses:** USE the `mockApiSuccess<TData>(data)` and `mockApiError(error)` helpers from `tests/mockHelpers.ts` to satisfy the complex Hey-API signature without polluting tests.
- **Flushing Svelte Reactivity:** Waiting for DOM updates after an API call requires flushing both the microtask queue and Svelte's tick:
  ```typescript
  const flushPromises = async () => {
    await tick();
    await new Promise((r) => setTimeout(r, 0));
    await tick();
  };
  ```

## 4. Maintenance

- **AST Integrity:** Use Nuclear Block Replacements (entire `describe`/`it` blocks). NEVER use loose line-deletion commands that break AST structure.
- **Kill Zombie Tests:** If you fix an architectural root cause (e.g., adding `notion_id`), aggressively DELETE old tests written to verify the legacy workarounds.

## 1. Meta-Prompting & AI Constraints

- **ABSOLUTE CONSTRAINTS ONLY:** ALWAYS use absolute terms (MUST, NEVER, BANNED, STRICTLY). NEVER use polite/emotional language ("Please", "Try to", "Avoid") as it dilutes LLM token weights.
- **ATOMIZE PROMPTS:** Break instructions down into atomized, file-specific prompts. Monolithic prompts cause agents to gloss over critical lines of code.

## 2. The OpenAPI SDK Pipeline

- **Backend Change Impact:** ANY backend change to a Pydantic model or FastAPI router REQUIRES running the generation pipeline to keep the frontend SDK in sync.
- **Generation Workflow:** Run `uv run scripts/export_openapi.py`, then `cd frontend && bun run typegen` (Lefthook runs this pre-commit).
- **Synchronization:** Backend and frontend MUST remain in sync strictly through the auto-generated SDK. Manual interface definitions are BANNED.

## 3. Rule Governance & Verification

- **Source of Truth:** Edit rules ONLY in the `docs/ai-rules/` directory. NEVER directly edit generated artifacts (`.clinerules`, `.windsurfrules`).
- **Compilation:** ALWAYS run `bun run scripts/generate-ai-instructions.ts` after editing rules to propagate them to agent configs.
- **Pre-Commit:** Validate with `bun run build && bun run lint && bun run typecheck`. NEVER rely on CI/CD to catch Svelte syntax or type errors.
