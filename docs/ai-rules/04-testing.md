---
id: testing
title: Pillar 4 - Testing & Validation
priority: 40
---
## Execution Rules
- **CRITICAL:** NEVER use `bun test`. Always run tests using `bun run test`.
- **Backend:** Run using `uv run python -m pytest -q`.

## Backend Testing
- Use `pytest` for all backend tests. Test files should be `test_*.py` and co-located with their respective implementation files.
- Mock external dependencies (like Notion API) using `unittest.mock`.
- Test database operations exclusively using an in-memory SQLite database (`:memory:`).

## Frontend Testing
- **Framework:** Vitest + `@testing-library/svelte`.
- **State Mocking (CRITICAL OVERWRITE):** Do NOT use `vi.mock()` on `.svelte.ts` files that contain `$state` runes. State files must be tested using integration-style testing methodologies. 
- **DOM Accessibility:** Testing for buttons MUST use accessible queries (e.g., `screen.getByRole('button', { name: /Text/i })`). Do NOT use `getByText()` for buttons because emojis and text are structurally separated. For `iconOnly` buttons, rely on their `title` attribute, which `getByRole` uses as the accessible name.
