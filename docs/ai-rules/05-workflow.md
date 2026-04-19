---
id: workflow
title: Pillar 5 - Workflow & Git Rules
priority: 50
---

## 1. Meta-Prompting & AI Constraints

- **ABSOLUTE CONSTRAINTS ONLY:** ALWAYS use absolute terms (MUST, NEVER, BANNED, STRICTLY). NEVER use polite/emotional language ("Please", "Try to", "Avoid") as it dilutes LLM token weights.
- **ATOMIZE PROMPTS:** Break instructions down into atomized, file-specific prompts. Monolithic prompts cause agents to gloss over critical lines of code.

## 2. The OpenAPI SDK Pipeline

- **Backend Change Impact:** ANY backend change to a Pydantic model or FastAPI router REQUIRES running the generation pipeline to keep the frontend SDK in sync.
- **Generation Workflow:** Run `uv run scripts/export_openapi.py`, then `cd frontend && bun run typegen` (Lefthook runs this pre-commit).
- **Synchronization:** Backend and frontend MUST remain in sync strictly through the auto-generated SDK. Manual interface definitions are BANNED.

## 3. Rule Governance & Verification

- **Source of Truth:** Edit rules ONLY in the `docs/ai-rules/` directory. NEVER directly edit generated artifacts (`.clinerules`, `.windsurfrules`).
- **Compilation:** ALWAYS run `bun run scripts/generate-ai-instructions.ts` after editing rules to propagate them to agent configs.
- **Pre-Commit:** Validate with `bun run build && bun run lint && bun run typecheck`. NEVER rely on CI/CD to catch Svelte syntax or type errors.
