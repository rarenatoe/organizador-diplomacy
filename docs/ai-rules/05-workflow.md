---
id: workflow
title: Pillar 5 - Workflow & Git Rules
priority: 50
---

## Meta-Prompting & AI Communication

- **ABSOLUTE CONSTRAINTS ONLY:** When writing or updating rules, ALWAYS use absolute constraints (MUST, NEVER, BANNED, STRICTLY). NEVER use polite/emotional language ("Please", "Try to", "Avoid") as it dilutes token weights and probabilistic constraints.
- **LOGICAL GROUPING:** Group concepts with bullet points rather than repetitive "Rule / Anti-Pattern" boilerplate. Use clear headers and concise directives.
- **TOKEN EFFICIENCY:** Every word MUST serve a constraint purpose. Eliminate filler language and maximize information density.

## Rule Governance

- **Source of Truth:** Store AI rules in `docs/ai-rules/` directory. NEVER directly edit generated artifacts (`.clinerules`, `.windsurfrules`, `.github/copilot-instructions.md`).
- **Compilation:** ALWAYS run `bun run scripts/generate-ai-instructions.ts` after editing any markdown files in `docs/ai-rules/`. NEVER skip compilation as it causes inconsistencies across AI instruction files.

## Verification & Commits

- **Pre-Commit Validation:** ALWAYS validate with `bun run build && bun run lint && bun run typecheck`. NEVER commit without proper validation.
- **Local Syntax Checking:** ALWAYS check Svelte syntax problems locally. NEVER rely on CI/CD to catch syntax issues.
- **Commit Format:** Use conventional prefixes: `feat:`, `fix:`, `refactor:`, `test:`. NEVER use non-standard formats that break changelog generation.
