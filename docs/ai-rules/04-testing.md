---
id: testing
title: Pillar 4 - Testing & Validation
priority: 40
---

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
