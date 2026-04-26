---
id: testing
title: Pillar 4 - Testing & Validation
priority: 40
---

## 1. Backend Testing (`pytest`)

- **Environment:** Use `:memory:` SQLite and `unittest.mock`. BANNED: Real external API hits.
- **Assertions:** Use object attribute dot-notation (`result.players`). BANNED: Dict key access (`result["players"]`), guaranteeing Pydantic compliance.
- **Algorithms:** Explicitly test edge cases: length disparities, typo variants, accents, abbreviations.
- **Math Setup:** Explicitly comment integer division math in test setups to prevent off-by-one failures.

## 2. Frontend Testing (`vitest`)

- **State:** Test `.svelte.ts` logic files in isolation. BANNED: DOM mounting for pure logic.
- **Isolation:** ALWAYS wipe globally exported class/state instances in `beforeEach()`.
- **DOM Queries:** Use semantic queries (`getByRole`). Normalize whitespace on i18n dates to match Testing Library's DOM handling.
- **Structural Guards:** Assert the presence of abstraction CSS classes to prevent regressions that decouple layouts back into raw `{#each}` loops.
- **Snippets:** Use `createRawSnippet`. BANNED: Weakening a component's API to bypass test errors. Create `.test.svelte` wrapper files for layout snippet tests.

## 3. SDK Mocking Patterns (CRITICAL)

- **Direct Mocking:** ALWAYS mock `../../generated-api/sdk.gen` directly in `vi.mock()`. BANNED: Mocking the `index.ts` barrel file.
- **Default Mocks:** EVERY called SDK function MUST have a `mockResolvedValue` in `beforeEach()` to prevent silent `onMount` crashes.
- **Payload Helpers:** Use `mockSdkSuccess` / `mockSdkError` to replicate the `{ data, error, request, response }` tuple.
- **Flushing:** Flush the microtask queue AND Svelte's tick twice when awaiting API-driven DOM updates.

## 4. AST & Maintenance

- **AST Integrity:** Use Nuclear Block Replacements (replace entire `describe`/`it` blocks). BANNED: Loose line-deletions that break AST.
- **Zombie Tests:** Aggressively delete old tests written to verify legacy workarounds when root causes are fixed.
