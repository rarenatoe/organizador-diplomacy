# Contributing Guide

Thank you for your interest in contributing to the Diplomacy Games Organizer! To maintain code health, we have strict architectural guidelines.

## 🏗 Architectural Rules (AI Rules)

This repository enforces strict rules for both human developers and AI assistants. **Please read the `docs/ai-rules/` folder before contributing.**

Key principles:
1. **Frontend as the Source of Truth (for drafting):** The frontend manages the in-memory state for manual drafting. The backend mathematically overwrites and validates the data, without hidden merges or "magic".
2. **Svelte 5 Runes:** Only `$state`, `$derived`, and `$effect` are permitted. Using classes to manage state is strictly forbidden.
3. **OpenAPI SDK:** Communication between the Frontend and Backend *must* happen through the auto-generated `@hey-api` client. (Run `bun run typegen` if you modify the backend).
4. **Strict Validation:** No magic dictionaries (`dict[str, Any]`). Use explicit types (`TypedDict` or `Pydantic` in Python).

## 🧑‍💻 Development Workflow

1. **Create your branch:**
   ```bash
   git checkout -b feature/my-new-feature
   ```
2. **Make your changes** respecting the architectural layers (Domain-Driven Design).
3. **Check types and linters:**
   The project uses `lefthook` as a pre-commit, but you can run the tools manually:
   ```bash
   bun run lint
   bun run typecheck
   uv run ruff check backend/
   ```
4. **Regenerate the API client** (if applicable):
   ```bash
   bun run typegen
   ```
5. **Run the tests** (Mandatory for shared logic):
   ```bash
   bun run test
   uv run pytest
   ```
6. **Submit your Pull Request**.