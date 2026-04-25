---
id: testing
title: Pillar 4 - Testing & Validation
priority: 40
---

## 1. Execution & Strategy

- **Runners:** Frontend: `bun run test` (Vitest). Backend: `uv run python -m pytest -q`.
- **Backend Mocking:** Use `unittest.mock` for external dependencies (e.g., Notion API). Use `:memory:` SQLite. NEVER hit real external APIs.
- **Frontend Querying:** Use semantic queries (`getByRole`, `getByPlaceholderText`). NEVER test implementation details or use fragile DOM traversal.
- **Backend Model Assertions:** When asserting structured API/view outputs in Python tests, ALWAYS use object attribute dot-notation (`response.mesas`, `result.players`). NEVER use dictionary key access (`response["mesas"]`, `result["players"]`). This enforces that response types are proper Pydantic models, not raw dicts.
- **Heuristic & Algorithm Testing:** When testing fuzzy matching, comparisons, or scoring algorithms, ALWAYS explicitly test realistic human edge cases. You MUST include test fixtures for: length disparities (e.g., "Eduardo G." vs "Eduardo González-Prada Arriarán"), typographical variants and accents, and prefixes/abbreviations. NEVER just test the "happy path" or identical strings.

## 2. Svelte & DOM Testing Rules

- **State Module Testing:** Logic extracted to `.svelte.ts` files MUST be tested in isolation as pure TypeScript. NEVER use DOM mounting for pure logic.
- **Singleton Resetting:** ALWAYS wipe globally exported class/state instances in `beforeEach()` to prevent test pollution.
- **Structural Regression Guards:** Explicitly test HTML hierarchy. When a layout is centralized into a shared container component (e.g., `Waitlist.svelte`), parent components MUST explicitly assert the presence of that specific abstraction's CSS class in their DOM (e.g., `expect(container.querySelector(".waitlist-container")).toBeInTheDocument()`). This guarantees future refactors do not accidentally decouple layouts back into raw `{#each}` loops.
- **DRY Renders & Fixtures:** Extensively mock data MUST live in `*.fixtures.ts`. EVERY test file MUST implement a centralized `renderComponent(overrides = {})` factory.
- **Snippet Testing:** Use `createRawSnippet` from `svelte` for snippet components. NEVER test without proper Svelte 5 snippet creation.
- **Snippet API Integrity:** NEVER weaken a component's API for testing convenience (e.g., changing `children: Snippet` to `children?: Snippet`) just to prevent Svelte 5 runtime `{@render}` errors.
- **Test Wrappers for Snippets:** To test layout or wrapper components that require Snippets, you MUST create a dedicated `.test.svelte` wrapper file (e.g., `MetaGridTestWrapper.test.svelte`). Render the wrapper in your test so the Snippet is populated with actual DOM nodes.
- **Selector Stability:** When testing structural hierarchy, ensure you are targeting the centralized layout classes (e.g., `.panel-section`) rather than legacy/generic utility classes.

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
