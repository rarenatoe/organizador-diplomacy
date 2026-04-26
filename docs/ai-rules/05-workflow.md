---
id: workflow
title: Pillar 5 - Workflow & Git Rules
priority: 50
---

## 1. Meta-Prompting Rules

- **Absolute Constraints:** Use MUST, NEVER, BANNED, STRICTLY. BANNED: Polite/suggestive language ("Please", "Try to").
- **Atomization:** Break instructions into focused, file-specific prompts to prevent AI context gloss-over.

## 2. OpenAPI SDK Pipeline

- **Generation:** ANY backend change to a Pydantic model or FastAPI router REQUIRES running `bun run typegen`
- **Sync:** Backend and frontend communicate STRICTLY through the generated SDK. BANNED: Manual interface definitions.

## 3. Rule Governance

- **Source of Truth:** Edit rules ONLY in `docs/ai-rules/*.md`. BANNED: Editing `.clinerules` or `.windsurfrules` directly.
- **Compilation:** Run `bun run ai-rules:generate` after editing rules to propagate them to agent configs.
- **Validation:** Let pre-commit hooks (`lefthook`) handle format/lint/typecheck.
