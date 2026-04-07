---
id: workflow
title: Pillar 5 - Workflow & Git Rules
priority: 50
---

## Rule Governance

**Rule:** Store AI rules in `docs/ai-rules/` directory as the source of truth.
**Anti-Pattern:** Directly editing `.clinerules`, `.windsurfrules`, or `.github/copilot-instructions.md` which are generated artifacts.

**Rule:** Run `bun run scripts/generate-ai-instructions.ts` after editing any markdown files in `docs/ai-rules/` to compile rules into root directory AI files.
**Anti-Pattern:** Editing AI rule files without running the compilation script, causing inconsistencies across AI instruction files.

## Verification & Commits

**Rule:** Validate all tests and typing before committing using `bun run build && bun run lint && bun run typecheck`.
**Anti-Pattern:** Committing changes without proper validation that may break the build or introduce errors.

**Rule:** Check for Svelte syntax problems locally before pushing changes.
**Anti-Pattern:** Relying on CI/CD to catch syntax issues that should be identified during development.

**Rule:** Use conventional commit prefixes: `feat:`, `fix:`, `refactor:`, `test:`.
**Anti-Pattern:** Using non-standard commit message formats that break automated changelog generation.
