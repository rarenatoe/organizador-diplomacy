## Canonical AI Rules

This directory is the single source of truth for all AI assistant instructions.

### File contract

Each canonical file must include YAML frontmatter with:

- `id`: stable rule identifier.
- `title`: human-readable title.
- `scope`: `project` or `language`.
- `priority`: integer used for deterministic output ordering.
- `outputs`: output file mapping used by the generator.
- `toolNotes`: optional per-tool guidance.
- `applyTo`: required when `scope: language`; list of path globs.

### Editing workflow

1. Edit files in `docs/ai-rules/`.
2. Run `bun run ai-rules:generate`.
3. Commit canonical files — generated files are staged automatically by the pre-commit hook.

Never edit generated files directly:

- `.github/copilot-instructions.md`
- `.github/python.instructions.md`
- `.github/typescript.instructions.md`
- `.clinerules`
- `.trae/rules/core.md`
- `.trae/rules/python.md`
- `.trae/rules/typescript.md`
