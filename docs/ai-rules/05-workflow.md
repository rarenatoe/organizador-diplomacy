---
id: workflow
title: Pillar 5 - Workflow & Git Rules
priority: 50
---
## Rule Governance
- AI rules live in `docs/ai-rules/`. 
- NEVER directly edit `.clinerules`, `.windsurfrules`, or `.github/copilot-instructions.md`. They are generated artifacts.

## Verification & Commits
- Validate all tests and typing before committing: `bun run build && bun run lint && bun run typecheck`.
- Check for Svelte syntax problems locally.
- Git Commits must follow conventional prefixes: `feat:`, `fix:`, `refactor:`, `test:`.
