---
id: testing
title: Pillar 4 - Testing & Validation
priority: 40
---

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
