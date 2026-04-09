---
id: testing
title: Pillar 4 - Testing & Validation
priority: 40
---

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
