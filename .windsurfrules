

## 1. Domain & Workflows

- **Core Entities:** `Snapshots` (rosters), `Games` (7-player tables + GMs), `Waitlists` (unseated).
- **History Lookup:** MUST use strict 4-tier traversal: `TimelineEdge` -> `SnapshotPlayer` -> `SnapshotHistory JSON` -> `NotionCache`. NEVER skip tiers.
- **Manual Save:** Frontend is the absolute source of truth. Backend strictly overwrites state. NEVER merge weights or apply smart corrections on manual saves.
- **Draft Pipeline & Reconciliation:** Calculate Tickets -> Distribute to Tables -> Assign Countries -> Mathematically Reconcile Waitlist. Treat complex algorithm outputs as "rough drafts". Both backend and frontend MUST use identical, deterministic mathematical reconciliation (e.g., `desired_games - seated_games = missing_slots`) to resolve final state instead of naive array patching.
- **Symmetric Optimistic UI:** When the frontend needs to react instantly to user mutations (like swapping players), it MUST execute the exact same deterministic math as the backend to rebuild the state. NEVER replicate complex backend algorithms in the UI; reduce the logic to shared mathematical truths.

## 2. Global Architecture & Language Boundaries

- **Backend Stack:** Python 3.13, uv, FastAPI, SQLAlchemy. NEVER use Flask or mix presentation logic.
- **Frontend Stack:** Svelte 5, TypeScript, Vite. NEVER place business logic in UI components.
- **Bilingual Codebase:** - **Internal Code:** English ONLY (variables, types, schemas, endpoints).
  - **UI Text:** Spanish ONLY (HTML labels, buttons, errors). NEVER translate user-facing text.
  - **API Payloads:** NEVER translate API-coupled data properties.

## 3. Domain-Driven Design (DDD)

- **Layer Separation:** - `organizador/`: Pure domain logic (Python dataclasses/TypedDicts). NO FastAPI/Pydantic imports.
  - `api/models/`: Pydantic DTOs. MUST expose `@classmethod def from_domain(cls, obj) -> "Self"` factories.
  - `api/routers/`: HTTP routing only. Validate input -> Call CRUD/Domain -> Call DTO factory.
- **Data Flow:** Downward only (Router → CRUD/Domain → DTO). Domain layer MUST NEVER reference DTOs.
- **Separation of Concerns:** Backend delivers structured primitives (e.g., `list[str]`). Frontend handles presentation/formatting (e.g., joining strings).

## 4. Algorithm & Degradation Principles

- **Graceful Degradation:** Favour partial matches (e.g., abbreviated names) over strict failures. Cap excessive user limits (e.g., too many GMs) instead of blocking the UI.
- **Relative Thresholds:** Use dynamic baselines (e.g., table minimums) for algorithms, NEVER hardcoded absolute limits.
- **Greedy Optimization:** Prefer Greedy Intervention loops over linear passes for complex assignments. Score assignments by simultaneous constraint resolutions.

## 1. Database & Schema (`aiosqlite`)

- **Schema Management:** Define strictly in code. BANNED: Persistent external DBs, Alembic migrations.
- **Identity & Graphs:** Use `graph_nodes` for universal IDs. Anchor identity to immutable `notion_id`, not user-editable names. Flow data through immutable snapshots via `timeline_edges`.
- **Deep Cascades:** Use recursive cascade functions for tree/graph deletions. NEVER use shallow loops.
- **Data Sanitization:** Map raw SQL `Row` results into Pydantic models at the `crud/` layer. Sanitize/coerce types before validation.
- **Collections:** Use SQLAlchemy `JSON`. DTOs/DB models MUST default to `[]`. BANNED: `""` or `None` for lists.

## 2. API & Logic Boundaries

- **Repository Pattern:** Group CRUD operations by domain (`backend/crud/`). NEVER cram operations into single files or mix domains.
- **Strict API Purity:** Backend MUST NEVER send formatted UI strings (e.g., `"Antiguo (15 juegos)"`). APIs MUST send strictly typed primitive data.
- **Synchronized CQRS:** When altering a schema or write payload, you MUST simultaneously update aggregate SQL views and their TS interfaces.
- **Two-Step Generation:** Enforce `/api/game/draft` (in-memory) followed by `/api/game/save` (persistence). NEVER write draft data directly to DB.
- **Strict SDK Optionality:** If the frontend strictly requires a field, DO NOT assign a default value in the Pydantic response model. Default values in Pydantic implicitly mark fields as optional (`?`) in the generated TypeScript.
- **Strict Primitives:** Eliminate `None`/`null` for calculable numeric or boolean states. Use strict types (e.g., `int` defaulting to `0` behind the scenes) to eradicate defensive `?? 0` fallback checks in the frontend UI.
- **Eradication of Type Cancer:** NEVER use `dict[str, Any]` across architectural boundaries, **with ONE strict exception:** passing serialized Pydantic writes (`model_dump(mode="json")`) from Routers into CRUD functions. Everywhere else, use typed `TypedDict` or Pydantic models.
- **Absolute Trimming:** API response Pydantic models MUST contain ONLY the exact fields the frontend UI consumes. NEVER expose additional fields just because they were queried from the database. Each response model is a deliberate contract, not a DB row mirror.
- **Named Types for Unions (RootModel):** When frontend components need to reference a complex union type used across multiple fields (e.g., `str | int | bool | None`), NEVER define them inline repeatedly in Pydantic models. Inline unions cause the OpenAPI generator to emit anonymous types that can trigger ESLint's `no-duplicate-type-constituents` when extracted or combined in TypeScript. ALWAYS define an explicit `RootModel` (e.g., `class FieldValue(RootModel[str | int | bool | None]): pass`) so the frontend SDK generates and exports a clean, strongly-typed named alias.

## 3. Performance & Python ISP

- **Query Optimization:** Fetch ONLY required columns. NEVER remove restricting `.join()` clauses (causes Cartesian fan-outs). Use `.in_()` subqueries for bulk deletions to prevent N+1.
- **Interface Segregation:** Pure functions declare minimal `TypedDict`s instead of demanding massive ORM models. Use covariant hints (`Mapping`, `Sequence`).
- **String Normalization:** Aggressively normalize human strings (lowercase, strip, collapse spaces, remove accents) for comparisons.
- **Logging:** Use `backend.core.logger`. BANNED: `print()`, `pprint()`.

## 1. Svelte 5 Reactivity & State

- **Runes ONLY:** USE `$state`, `$derived`, `$effect`. BANNED: `let` for reactivity, ES6 Classes for state.
- **State Architecture:** Group related states in Discriminated Unions. Extract complex state into POJOs using `lowerCamelCaseState.svelte.ts` files. Use an array stack for navigation.
- **Thick Logic Extraction:** Complex data mutations (e.g., drag-and-drop, multi-array swapping, draft orchestrations) MUST be extracted into a dedicated `.svelte.ts` controller. NEVER leave massive (50+ line) mutation functions inside `.svelte` script blocks.
- **Deterministic State Rebuilding:** When users perform complex mutations (like multi-array swaps), NEVER surgically patch array indexes (which causes duplicates). Always re-run a deterministic mathematical pass over the entire state to rebuild derived lists.
- **Declarative Transformations:** Use modern declarative chains (`Object.values().map().filter().sort()`) instead of imperative `for...in` loops to derive state.
- **Loop Constants:** ALWAYS use Svelte's `{@const ...}` to compute derived target objects or parameters within `{#each}` loops. NEVER instantiate new objects inline inside HTML event handlers (e.g., `onclick={() => fn({ id })}`).
- **Typing:** Use component-level Generics (`<script lang="ts" generics="...">`) so components adapt safely to diverse data shapes.
- **Snippet Event Handlers:** NEVER use inline arrow functions for event handlers inside HTML elements within Svelte 5 `{#snippet}` blocks or `{#each}` loops (e.g., `onchange={(e) => update(i)}`). ALWAYS declare them first using `{@const handleChange = (e: Event) => update(i)}` and pass the reference. This ensures strict Svelte 5 architectural compliance and prevents reactive instantiation bugs.
- **Immutable Array Mutations:** BANNED: `Array.prototype.splice()`. NEVER mutate array states surgically. To remove an item, ALWAYS rebuild the array deterministically using `.filter((_, i) => i !== targetIndex)`.

## 2. Auto-Generated SDK (`@hey-api`)

- **Single Source of Truth:** Import all domain types from `src/generated-api`. BANNED: Manual `fetch` calls, manual domain interfaces in `src/types.ts`.
- **Response Unpacking:** ALWAYS unpack immediately: `const { data, error } = await apiEndpoint()`. Handle `error` explicitly.
- **Error Handling:** Intercepted globally in `api/client.ts`. Use typed unions for error parsers, NEVER `any`/`unknown`.

## 3. Layout & CSS Grid (Rule of 8)

- **Styling:** Pure CSS only. Use semantic variables (`var(--space-8)`). BANNED: Tailwind, utility classes, inline `style="..."`.
- **Class Injection:** Use `cx()`/`clsx`. BANNED: String concatenation.
- **Intrinsic Sizing:** Leaf components MUST NOT define external margins. Parents dictate spacing via `display: flex; gap: ...`. Wrap target selectors in `:global()`.
- **Grid Blowout:** Apply `min-width: 0` to flex containers and children inside CSS Grids.
- **Structural Abstractions:** Create wrapper components (`<PanelSection>`) instead of copy-pasting layout classes.

## 4. UI Architecture & UX

- **Smart vs Dumb Components:** `features/` are Smart components that handle API side-effects and complex state orchestration. `ui/` and `layout/` are Dumb components that MUST remain domain-agnostic and bubble actions via callback props. NEVER perform API calls in Dumb components.
- **References:** Swap entire object references for complex nested objects. BANNED: Deep mutations of nested properties.
- **Snippets:** Presentation lists must be dumb. Use Svelte 5 Snippets to yield domain logic (indices, IDs) back to the parent. Abstract entire list containers, not just leaf items.
- **UX Guards:** Mimic padding in read-only states and set `min-height` to prevent layout shifts. NEVER use UI-layer fallbacks (e.g., `{cupos ?? deseadas}`) to mask inaccurate underlying data; fix the mathematical source of truth. Pair floating UI visibility with explicit interaction booleans to prevent zombies.
- **Banned Browser APIs:** NEVER use `window.prompt()`, `window.alert()`, or `window.confirm()`. ALWAYS use custom modal components.
- **Dates:** Cast naive backend timestamps to UTC (`+ "Z"`) before parsing to adapt to local timezones. ALWAYS use the shared `formatDate` utility from `src/i18n.ts`.

## 1. Backend Testing (`pytest`)

- **Environment:** Use `:memory:` SQLite and `unittest.mock`. BANNED: Real external API hits.
- **Assertions:** Use object attribute dot-notation (`result.players`). BANNED: Dict key access (`result["players"]`), guaranteeing Pydantic compliance.
- **Algorithms:** Explicitly test edge cases: length disparities, typo variants, accents, abbreviations.
- **Math Setup:** Explicitly comment integer division math in test setups to prevent off-by-one failures.
- **Mirrored Test Coverage:** Any business logic duplicated across the stack (e.g., state reconciliation math) MUST have parallel unit tests in both `pytest` and `vitest` asserting the exact same scenarios and edge cases.

## 2. Frontend Testing (`vitest`)

- **State:** Test `.svelte.ts` logic files in isolation. BANNED: DOM mounting for pure logic.
- **Isolation:** ALWAYS wipe globally exported class/state instances in `beforeEach()`.
- **DOM Queries:** Use semantic queries (`getByRole`). Normalize whitespace on i18n dates to match Testing Library's DOM handling.
- **Structural Guards & Selectors:** Assert the presence of abstraction CSS classes (e.g., `.panel-section`). NEVER query by generic, partial class names (e.g., `.section`) or use `.closest()` loosely, as CSS abstractions frequently evolve.
- **Snippets:** Use `createRawSnippet`. BANNED: Weakening a component's API to bypass test errors. Create `.test.svelte` wrapper files for layout snippet tests.

## 3. SDK Mocking Patterns (CRITICAL)

- **Direct Mocking:** ALWAYS mock `../../generated-api/sdk.gen` directly in `vi.mock()`. BANNED: Mocking the `index.ts` barrel file.
- **Default Mocks:** EVERY called SDK function MUST have a `mockResolvedValue` in `beforeEach()` to prevent silent `onMount` crashes.
- **Payload Helpers:** Use `mockSdkSuccess` / `mockSdkError` to replicate the `{ data, error, request, response }` tuple.
- **Flushing:** Flush the microtask queue AND Svelte's tick twice when awaiting API-driven DOM updates.

## 4. AST & Maintenance

- **AST Integrity:** Use Nuclear Block Replacements (replace entire `describe`/`it` blocks). BANNED: Loose line-deletions that break AST.
- **Zombie Tests:** Aggressively delete old tests written to verify legacy workarounds when root causes are fixed.

## 1. Meta-Prompting Rules

- **Absolute Constraints:** Use MUST, NEVER, BANNED, STRICTLY. BANNED: Polite/suggestive language ("Please", "Try to").
- **Atomization:** Break instructions into focused, file-specific prompts to prevent AI context gloss-over.

## 2. OpenAPI SDK Pipeline

- **Generation:** ANY backend change to a Pydantic model or FastAPI router REQUIRES running `bun run typegen`
- **Sync:** Backend and frontend communicate STRICTLY through the generated SDK. BANNED: Manual interface definitions.

## 3. Rule Governance

- **Source of Truth:** Edit rules ONLY in `docs/ai-rules/*.md`. BANNED: Editing `.clinerules` or `.windsurfrules` directly.
- **Compilation:** Run `bun run ai-rules:generate` after editing rules to propagate them to agent configs.
- **Validation:** Let pre-commit hooks (`lefthook`) handle format/lint/typecheck.
