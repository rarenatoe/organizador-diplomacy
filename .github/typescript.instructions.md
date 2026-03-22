---
applyTo: "frontend/src/**"
---

## TypeScript conventions
- All domain interfaces live in `src/types.ts` — export everything from there.
- Module responsibilities: `chain.ts` → renderers; `selection.ts` → state; `clipboard.ts` → copy store; `panels.ts` → panel content; `app.ts` → entry point wiring.
- Import graph (no cycles): `app.ts` → `chain`, `selection`, `panels`. `panels.ts` → `chain`, `clipboard`, `selection`. `chain.ts` → `selection`. `clipboard.ts` → none.
- Run `bun run build` to bundle into `static/app.js` (IIFE, no `type="module"` needed). `bun run typecheck` for type-only check. `bun run lint` — ESLint strict.
- All DOM interactions use `!` non-null assertion (acceptable — developer controls the HTML).
- No `onclick` attributes in HTML — all event listeners in `src/app.ts`.
- No `String()`, no `!!bool` — use the typed value directly.

## UI conventions
- `index.html` is a ~57-line Jinja2 shell. **No logic here, no onclick attributes** — event listeners wired in `src/app.ts`.
- All CSS in `static/style.css`. All JS compiled from `src/app.ts` (entry point) → `static/app.js`.
- **Click-to-select**: snapshot node click → `setSelectedSnapshot(id)` → `.csv-selected` green ring + button label "Organizar · #N".
- Game node click → `openGame(id)` → GET `/api/game/<id>`, shows detail panel.
- Sync node click → `openSyncPanel(id)` → searches chain data for the edge, shows metadata panel.
- `runScript("organizar", getSelectedSnapshot())` reads selection from `src/selection.ts`. `deselectSnapshot()` resets.
- `renderSnapshotTree()` in `src/chain.ts` renders the chain recursively — branches stacked vertically so no false arrow.

## Planned migrations
- **Framework (Vue/React)**: currently deferred. The refactor into `chain`, `selection`, `clipboard`, `panels` modules resolved the immediate size/complexity problem. Reassess when a state change needs to drive multiple independent UI regions simultaneously (the trigger for reactive data binding). The bundler (`bun build`) is already in place.
