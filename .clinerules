

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
- **Graceful Degradation on Incomplete Data:** Algorithms resolving user identity or matching entries must account for incomplete data representation across systems (e.g., Notion vs Local DB). A partial representation (like an abbreviated middle/last name) that strongly matches a subset of a fully fleshed-out entry must be scored favorably, rather than heavily penalized for strict word-length mismatches.
- **Graceful Degradation over Strict Blocking:** When the user supplies configuration that exceeds a logical limit (e.g., assigning more GMs than available tables), DO NOT block the UI or throw backend errors unless it fundamentally breaks data integrity. Prioritize the most eligible subjects (e.g., pure GMs who want 0 games), cap the resources for the rest to valid limits, and allow the system to proceed smoothly.
- **Relative vs. Absolute Thresholds:** In long-running leagues, absolute thresholds degrade over time. Domain algorithms MUST define constraints (like "curses" or disproportionate repetitions) relative to a dynamic baseline (e.g., the table minimum or the player's personal minimum), rather than hardcoded absolute limits.
- **Greedy Optimization over Linear Checks:** For complex assignment logic (like country distribution), prefer Greedy Intervention loops over linear passes. Score potential assignments by how many constraints they resolve simultaneously (e.g., "Self-Healing" vs. "Shielding") to mathematically minimize total forced interventions.

## 5. Domain-Driven Design (DDD) & DTO Separation

- **Domain Model Purity:** Core business logic in `organizador/` (e.g., weight calculations, distribution algorithms) MUST NEVER import FastAPI, Pydantic, or any web framework. Domain models are plain Python dataclasses or TypedDicts only.
- **Strict Layer Boundaries:** `organizador/` owns Domain Models. `api/models/` owns DTOs (Pydantic). `api/routers/` owns HTTP concerns only. NEVER collapse these layers.
- **Factory Methods on DTOs:** Pydantic response models in `api/models/` MUST expose a `@classmethod def from_domain(cls, obj: DomainModel) -> "Self"` factory to translate Domain Models into API responses. NEVER perform this translation inside a router function.
- **Lean Routers:** FastAPI routers MUST only: validate input, call a CRUD or domain function, call the DTO factory, and return. NEVER embed business logic or data reshaping directly in router functions.
- **No Upward Coupling:** Domain layer (`organizador/`) MUST NEVER reference DTO models from `api/models/`. Data flows strictly downward: Router → CRUD/Domain → DTO factory → Response.
- **Structured Data over Pre-Formatted Strings (Separation of Concerns):** The backend MUST deliver structured data (e.g., `list[str]` for multiple reasons or logs). NEVER pre-join strings or apply UI formatting (like bullet points or line breaks) in the backend. Let the frontend dictate the presentation.

## 1. Database & Schema

- **Database System:** Use disposable local SQLite (`aiosqlite`). NEVER use persistent external DBs or Alembic migrations. Define schema strictly in code.
- **Universal IDs:** Use centralized `graph_nodes` table for universal IDs and cascading deletes. NEVER implement separate ID systems.
- **Deep Recursive Cascades for Graphs:** When deleting entities tied to a tree or graph (like Snapshots and TimelineEdges), NEVER use shallow, manual loops to delete incoming and outgoing edges. ALWAYS use a dedicated, recursive cascade function that calls itself on child nodes to sever edges and prevent orphaned "stray nodes".
- **Immutable Identity:** ALWAYS anchor to immutable external IDs (`notion_id`). NEVER rely on user-editable strings (`name`) for relational mapping.
- **Immutable Snapshots:** Flow data through immutable snapshots connected by `timeline_edges`. NEVER create mutable historical data structures.
- **Fortifying the Database Boundary:** Raw SQL results from `db/views.py` MUST be immediately mapped into strict Pydantic models at the data access layer. NEVER pass raw `Row` objects or dicts with unsanitized DB values (e.g., SQLite ISO date strings) beyond the `crud/` layer. Sanitize and coerce types (dates, enums) before Pydantic validation.
- **JSON Column Strictness:** When migrating columns to hold collections (like lists of strings), ALWAYS use SQLAlchemy's `JSON` type. Ensure Pydantic DTOs and DB models strictly expect `list[str]` and default to `[]`, NEVER `""` or `None`, to prevent cascading validation crashes when reading from or writing to the database.

## 2. API & Logic Boundaries

- **Repository Pattern:** Group CRUD operations by domain (`backend/crud/`). NEVER cram operations into single files or mix domains.
- **Strict API Purity:** Backend MUST NEVER send formatted UI strings (e.g., `"Antiguo (15 juegos)"`). APIs MUST send strictly typed primitive data.
- **Synchronized CQRS:** When altering a schema or write payload, you MUST simultaneously update aggregate SQL views and their TS interfaces.
- **Two-Step Generation:** Enforce `/api/game/draft` (in-memory) followed by `/api/game/save` (persistence). NEVER write draft data directly to DB.
- **Eradication of Type Cancer:** NEVER use `dict[str, Any]` across architectural boundaries. Every API endpoint MUST return a strictly defined Pydantic response model. Internal functions that pass data between layers MUST use typed `TypedDict` or Pydantic models, not bare dicts.
- **Absolute Trimming:** API response Pydantic models MUST contain ONLY the exact fields the frontend UI consumes. NEVER expose additional fields just because they were queried from the database. Each response model is a deliberate contract, not a DB row mirror.
- **Named Types for Unions (RootModel):** When frontend components need to reference a complex union type used across multiple fields (e.g., `str | int | bool | None`), NEVER define them inline repeatedly in Pydantic models. Inline unions cause the OpenAPI generator to emit anonymous types that can trigger ESLint's `no-duplicate-type-constituents` when extracted or combined in TypeScript. ALWAYS define an explicit `RootModel` (e.g., `class FieldValue(RootModel[str | int | bool | None]): pass`) so the frontend SDK generates and exports a clean, strongly-typed named alias.

## 3. Performance & SQLAlchemy "Fat Trimming"

- **Explicit Selection:** Fetch ONLY required columns (`select(NotionCache.notion_id, NotionCache.name)`). NEVER fetch entire models (`select(NotionCache)`) for read-only algorithms.
- **The Cartesian Trap:** When optimizing queries, NEVER remove `.join()` clauses if they restrict relational mapping. Missing joins cause cross-join fan-outs.
- **Type-Safe Mapping:** Explicitly map SQLAlchemy `Row` objects into typed dicts (`{"name": row.name}`). Avoid `**row.mappings()` to guarantee Pyright compile-time safety.
- **Bulk Deletions (Prevent N+1 Queries):** Avoid looping over ORM objects in Python just to delete their children (e.g., querying `tables` and doing `for table in tables: delete(players)`). ALWAYS use SQLAlchemy subqueries and `.in_()` clauses to execute bulk relational deletes directly in the database.

## 4. Python Typing & ISP

- **Minimal TypedDicts (ISP):** Pure functions MUST declare a minimal `TypedDict` representing exactly what they need, rather than demanding massive DB models.
- **Covariant Hints:** Use `collections.abc.Mapping` and `Sequence` in type hints so functions accept both slim and ORM-derived dicts.
- **Hashing Keys:** ALWAYS hash by primitive attributes (`.name`). NEVER pass Pydantic models as dict/Counter keys.
- **Front-to-Back Honesty:** Do NOT overuse `Optional` / `| None` types in API response models. ALWAYS force default values to empty primitives (`""` instead of `None`, `[]` instead of `None`) unless `null` is a semantically meaningful value the frontend must distinguish from empty. Nullable fields MUST be documented with an explicit reason.

## 5. Coding Standards & Logging

- **Logging:** ALWAYS use `from backend.core.logger import logger` with appropriate levels. Use `exc_info=True` for exceptions. NEVER use `print()` or `pprint()`.
- **Real-World String Normalization:** Human-entered strings (like names) are messy. ALWAYS normalize strings used in comparisons or fuzzy matching algorithms. This MUST include: converting to lowercase, stripping surrounding whitespace, collapsing internal multiple spaces, and aggressively removing accents/diacritics (e.g., using `unicodedata.normalize("NFKD", ...).encode("ascii", "ignore")`). NEVER rely on raw strict equality or basic `.lower()` for human names.

## 1. Svelte 5 Reactivity & State

- **Runes ONLY:** USE `$state`, `$derived`, `$effect`. NEVER use `let` for reactive state. Use `$derived.by()` for complex logic.
- **Functional POJO State:** Extract complex state into plain objects using Runes, NEVER ES6 Classes.
- **Discriminated Unions:** Group related state variables (e.g., `status: 'idle' | 'resolving'`) into Discriminated Unions to eliminate impossible states.
- **Navigation Stack:** USE an in-memory stack (array) for multi-level navigation. NEVER use flat variables (`$state(panelId)`).
- **Logic File Naming:** NEVER name a logic file identically to a UI file (e.g., avoid `Component.svelte` and `Component.svelte.ts`). Use `lowerCamelCaseState.svelte.ts` to prevent bundler collisions.
- **Component-Level Generics:** Use component-level Generics (`<script lang="ts" generics="T extends {...}">`) so components adapt safely to diverse data shapes.

## 2. Auto-Generated API SDK (CRITICAL)

- **NO MANUAL FETCHING:** NEVER write manual `fetch` calls or custom interfaces. ALWAYS use the `@hey-api` generated endpoints (e.g., `apiPlayerCheckSimilarity`) and types from `frontend/src/generated-api`.
- **SDK as Single Source of Truth:** The generated SDK (`frontend/src/generated-api`) is the ABSOLUTE single source of truth for all domain types. NEVER manually define domain interfaces (e.g., `Game`, `Player`, `DraftResponse`) in `src/types.ts` or any other file. ALL domain types MUST be imported exclusively from `frontend/src/generated-api`. `src/types.ts` is reserved ONLY for purely UI-local types (e.g., `ToastState`, `EditPlayerRow`) that have no backend equivalent.
- **Explicit Response Unpacking:** ALWAYS unpack the `@hey-api` standardized response tuple immediately at the call site: `const { data, error } = await apiEndpoint()`. NEVER pass the raw response object to child components. Handle `error` explicitly before using `data`.
- **Global Error Handling:** FastAPI `422 ValidationErrors` are intercepted/normalized in `api/client.ts`. UI components MUST safely read `response.error` as a clean string. Legacy `api.ts` is DEPRECATED.
- **Robust API Error Parsing & Type Safety:** FastAPI `HTTPException`s (400/500) return `{ detail: "string" }`, which bypasses the standard 422 `HttpValidationError` (where detail is an array). ALWAYS use a heavily typed union (e.g., `HttpValidationError | { detail: string } | { error: string } | string`) for global error parsers. NEVER use `any` or `unknown` to bypass ESLint union rules, and NEVER cast error objects blindly using `String(error)`.

## 3. Layout, CSS Grid & The Rule of 8

- **Strict Rule of 8:** ALL spacing uses absolute variables (`var(--space-8)`). Borders (`1px`) are the ONLY exemption.
- **Pure CSS ONLY:** NEVER use Tailwind, utility classes, or inline `style="..."`. Use semantic variables (`var(--bg-secondary)`).
- **Class Injection:** ALWAYS use `cx()` or `clsx` for dynamic classes. NEVER use string concatenation (`class="{base} {active}"`).
- **Flexbox-in-Grid Blowout:** Apply `min-width: 0` to flex containers AND children inside CSS Grids to prevent `minmax()` blowout.
- **Svelte CSS Pruning:** Wrap dynamic target selectors in `:global()` (e.g., `.btn-icon :global(svg)`).
- **Sticky Stacking Contexts:** Elements inside `position: sticky` are trapped in its stacking context. To make an absolute child (like a dropdown) overlap, you MUST elevate the parent cell's z-index on focus/hover.
- **Intrinsic Sizing:** Leaf components MUST NOT define their own external margins. Parent layouts must govern spacing exclusively using `display: flex; gap: ...`.
- **Structural Abstractions over CSS Classes:** Do not copy-paste standard layout CSS (like `.section` or `.meta-grid`) across files. Instead, use or create Svelte structural wrapper components (e.g., `<PanelSection>`, `<MetaGrid>`).
- **Strict Intrinsic Sizing:** Leaf components and structural wrappers MUST NOT define external margins (`margin-top`, `margin-bottom`). The parent container must dictate spacing using `display: flex` and `gap`.
- **Zero Inline Styles:** Avoid using inline `style="..."` attributes for structural adjustments. Pass a `class` prop and use Svelte's `:global(.your-class)` modifier in the parent's `<style>` block.
- **Organized Imports:** All imports MUST be automatically sorted. NEVER manually order imports; rely on `@ianvs/prettier-plugin-sort-imports` via the format-on-save pipeline.

## 4. UI Architecture & UX

- **Component Routing:** `ui/` MUST be domain-agnostic. `features/` MUST be domain-aware.
- **Reference Swapping:** When exchanging complex nested objects, swap the entire object reference. NEVER manually overwrite individual properties.
- **Zero Layout Shift (Ghost Elements):** Read-only states MUST mimic the exact padding/height of editable states. Specifically, conditional ghost buttons or icons MUST NOT stretch grid/flex rows. Always set a strict `min-height` on the row container (e.g., `min-height: var(--space-32)`) to absorb conditional elements without shifting the layout.
- **Action Bubbling:** Feature components MUST bubble actions via callback props. NEVER perform API side-effects deeply in nested UI components.
- **Data Discovery:** NEVER rely on native HTML `title` attributes. ALWAYS use `<Tooltip>` components wrapping Svelte Snippets.
- **Array Rendering in Tooltips:** When rendering arrays of strings (like backend explanation logs) in tight spaces like Tooltips, join them contextually at the template level (`array.join(" ")`), rather than expecting the backend to pre-format them.
- **Banned Browser APIs:** NEVER use `window.prompt()`, `window.alert()`, or `window.confirm()`. ALWAYS use custom modal components.
- **Floating UI Guard:** Do not base the visibility of floating elements (dropdowns, modals) solely on derived array lengths. ALWAYS pair visibility with an explicit user-interaction boolean (e.g., `isActive`) to prevent zombie UI elements.
- **Logging:** ALWAYS use `logger.info()` from `src/utils/logger.ts`. NEVER use `console.log()`.
- **List-Level Abstraction Priority:** When standardizing repeated UI elements across different views (e.g., read-only vs. interactive), prioritize abstracting the _entire list container_ (e.g., `<Waitlist>`) rather than just the leaf item (`<WaitlistItem>`). This guarantees unified flex/grid `gap` spacing and eliminates duplicated `{#each}` loops in parent views.
- **Snippet Arguments for Domain Logic:** Presentation list components MUST remain entirely unaware of domain logic. Use Svelte 5 Snippet arguments (e.g., `actions?: Snippet<[number]>`) to yield contextual data (like loop indices or player IDs) back to the parent. The parent injects the UI (like `<Button>`) and handles the API side-effects.
- **Date & Time Formatting:** The backend often sends "naive" timestamps (e.g., `2024-01-01T10:00:00`). To ensure the browser correctly translates these to the user's local timezone, frontend formatters must explicitly cast them to UTC by appending a "Z" if it is missing before parsing them with `new Date()`. ALWAYS use the shared `formatDate` utility from `src/i18n.ts` rather than manually splitting or parsing strings in Svelte components.

## 1. Execution & Strategy

- **Runners:** Frontend: `bun run test` (Vitest). Backend: `uv run python -m pytest -q`.
- **Backend Mocking:** Use `unittest.mock` for external dependencies (e.g., Notion API). Use `:memory:` SQLite. NEVER hit real external APIs.
- **Frontend Querying:** Use semantic queries (`getByRole`, `getByPlaceholderText`). NEVER test implementation details or use fragile DOM traversal.
- **Backend Model Assertions:** When asserting structured API/view outputs in Python tests, ALWAYS use object attribute dot-notation (`response.mesas`, `result.players`). NEVER use dictionary key access (`response["mesas"]`, `result["players"]`). This enforces that response types are proper Pydantic models, not raw dicts.
- **Heuristic & Algorithm Testing:** When testing fuzzy matching, comparisons, or scoring algorithms, ALWAYS explicitly test realistic human edge cases. You MUST include test fixtures for: length disparities (e.g., "Eduardo G." vs "Eduardo González-Prada Arriarán"), typographical variants and accents, and prefixes/abbreviations. NEVER just test the "happy path" or identical strings.
- **Explicit Setup Math for Integer Divisions:** When testing algorithms that rely on integer division (e.g., `estimated_tables = tickets // 7`), be extremely careful with test setups. ALWAYS leave a comment explicitly summing the math in the test setup (e.g., `# 6 players + 1 GM = 7 tickets -> 1 table`) to ensure edge cases don't fail due to off-by-one division errors.

## 2. Svelte & DOM Testing Rules

- **State Module Testing:** Logic extracted to `.svelte.ts` files MUST be tested in isolation as pure TypeScript. NEVER use DOM mounting for pure logic.
- **Singleton Resetting:** ALWAYS wipe globally exported class/state instances in `beforeEach()` to prevent test pollution.
- **Structural Regression Guards:** Explicitly test HTML hierarchy. When a layout is centralized into a shared container component (e.g., `Waitlist.svelte`), parent components MUST explicitly assert the presence of that specific abstraction's CSS class in their DOM (e.g., `expect(container.querySelector(".waitlist-container")).toBeInTheDocument()`). This guarantees future refactors do not accidentally decouple layouts back into raw `{#each}` loops.
- **DRY Renders & Fixtures:** Extensively mock data MUST live in `*.fixtures.ts`. EVERY test file MUST implement a centralized `renderComponent(overrides = {})` factory.
- **Snippet Testing:** Use `createRawSnippet` from `svelte` for snippet components. NEVER test without proper Svelte 5 snippet creation.
- **Snippet API Integrity:** NEVER weaken a component's API for testing convenience (e.g., changing `children: Snippet` to `children?: Snippet`) just to prevent Svelte 5 runtime `{@render}` errors.
- **Test Wrappers for Snippets:** To test layout or wrapper components that require Snippets, you MUST create a dedicated `.test.svelte` wrapper file (e.g., `MetaGridTestWrapper.test.svelte`). Render the wrapper in your test so the Snippet is populated with actual DOM nodes.
- **Selector Stability:** When testing structural hierarchy, ensure you are targeting the centralized layout classes (e.g., `.panel-section`) rather than legacy/generic utility classes.
- **Testing Library & i18n Dates:** When testing UI components that render localized dates, `Intl.DateTimeFormat` often inserts invisible unicode spaces (like `\u202F`). Testing Library's `getByText` normalizes DOM whitespace to standard spaces, causing exact string matching to fail against raw formatter output. **DO NOT** use complex custom matcher callbacks. **DO** apply whitespace normalization to the expected string to match Testing Library's DOM normalization: `const expectedText = formatDate(dateStr).replace(/\s+/g, " "); expect(screen.getByText(expectedText)).toBeInTheDocument();`.

## 3. Auto-Generated SDK Testing Patterns (CRITICAL)

- **SDK Vitest Mocking:** ALWAYS mock `../../generated-api/sdk.gen` directly in `vi.mock()`. NEVER mock the barrel file (`../../generated-api`) as Vite module resolution bypasses `vi.mock` for auto-generated `index.ts` re-exports.
  - _Correct:_ `vi.mock("../../generated-api/sdk.gen", () => ({ apiGameDraft: vi.fn(), apiGameSave: vi.fn() }))`
  - _Incorrect:_ `vi.mock("../../generated-api", () => ...)`
- **Mock All Called Endpoints:** Every SDK function called by the component under test MUST be declared in the `vi.mock` factory AND given a default `mockResolvedValue` in `beforeEach()`. Missing mocks cause silent `undefined` returns that crash `onMount` blocks.
- **The Barrel File Trap:** Vite module resolution bypasses `vi.mock` for auto-generated `index.ts` files.
  - _Correct:_ `import * as api from "../../generated-api"; vi.spyOn(api, "apiPlayerGetAll").mockResolvedValue(...)`
  - _Incorrect:_ `vi.mock("../../generated-api", () => ...)`
- **Healthy Default Mocks:** Svelte `onMount` blocks will instantly crash if an API returns `undefined`. ALWAYS provide default `mockResolvedValue` spies in `beforeEach()`.
- **Mocking `@hey-api` Responses:** USE the `mockSdkSuccess(mockFn, data)` and `mockSdkError(mockFn, errorData)` helpers from `tests/mockHelpers.ts` to replicate the expected `{ data, error, request, response }` structure. NEVER construct this shape inline in tests. For return-value helpers use `mockApiSuccess(data)` and `mockApiError(error)` with `.mockResolvedValue()`.
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
