---
id: testing
title: Pillar 4 - Testing & Validation
priority: 40
---

## Testing Execution (CRITICAL)

**COMMANDS**:

- NEVER: `bun test`
- ALWAYS: `bun run test`
- Backend: `uv run python -m pytest -q`

## Backend Testing Strategy

**FRAMEWORK**: pytest
**TEST FILES**: `test_*.py` (co-located with implementation)
**DATABASE**: In-memory SQLite (`:memory:`) only

**MOCKING**:

- External dependencies: Use `unittest.mock`
- Notion API: Always mock, never hit real API
- Database operations: Test with in-memory SQLite

**TEST STRUCTURE**:

- Unit tests for pure functions
- Integration tests for database operations
- End-to-end tests for API endpoints

## Frontend Testing Strategy

**FRAMEWORK**: Vitest + `@testing-library/svelte`

**COMPONENT TESTING**:

- Unit tests for pure UI components
- Integration tests for stateful components
- Accessibility tests for interactive elements

**DOM QUERY PATTERNS**:

- Buttons: `screen.getByRole('button', { name: /Text/i })`
- NEVER: `getByText()` for buttons (emojis separated from text)
- Icon-only: Use `title` attribute for accessible name
- Forms: `screen.getByLabelText()`, `screen.getByPlaceholderText()`

**STATE TESTING** (CRITICAL):

- NEVER: `vi.mock()` on `.svelte.ts` files with `$state` runes
- USE: Integration-style testing methodology
- REASON: State files require real reactivity for accurate testing

## Test Maintenance (CRITICAL)

**DOM QUERY UPDATES**:

- CSS class changes → IMMEDIATELY update test queries
- Component extraction → Update all affected selectors
- Search patterns: `querySelector`, `closest`, `getBy` calls

**SYNCHRONIZE DOM QUERIES**:

- Whenever you abstract HTML into components, rename CSS classes, or translate Spanglish classes to English, you MUST immediately update `querySelector`, `closest`, and `getBy` calls in the corresponding `.test.ts` files. Legacy integration tests are the first thing to break during CSS/DOM refactors.

**FAILURE PREVENTION**:

- Legacy integration tests fail without query updates
- Run `bun run typecheck` after CSS changes
- Verify visual regression after component extraction

## Test Quality Standards

**ASSERTION PATTERNS**:

- Use semantic HTML queries first
- Test user behavior, not implementation details
- Assert accessible names, not visual appearance

**MOCKING PRINCIPLES**:

- Mock external dependencies only
- Test real component interactions
- Avoid over-mocking that hides real bugs

**COVERAGE REQUIREMENTS**:

- Critical user paths: 100% coverage
- Error handling: Always test error states
- Edge cases: Test null/undefined inputs
