# Diplomacy Games Organizer 🎲

Matchmaking and organization tool for the Diplomacy league. A full-stack application designed to manage rosters, sync player profiles from Notion, balance game tables (7 players + GM), and fairly assign countries using deterministic algorithms.

## 🚀 Key Features

- **Notion Synchronization:** Bi-directional integration to extract player stats, aliases, and historical match data.
- **Draft Generation (Tables):** Distribution algorithm that balances tables based on experience (newbies vs. veterans), respects priorities, and manages GM quotas.
- **Smart Country Assignment:** Utilizes a _Greedy Intervention Minimization_ strategy to prevent players from repeating the same nations, prioritizing self-healing assignments and "shield" players.
- **Conflict Resolution UI:** Dedicated UX flow to resolve name or alias collisions when importing players from CSV or Notion.
- **Graph-Based History:** The database (`aiosqlite`) preserves lineages of _Snapshots_ (rosters) and _Game Events_ immutably, allowing for reliable historical reconstructions.

## 🛠 Tech Stack

- **Backend:** Python 3.13, FastAPI, SQLAlchemy, `uv` (Package Manager).
- **Frontend:** Svelte 5, TypeScript, Vite.
- **API & SDK:** Strict OpenAPI type generation using `@hey-api/openapi-ts`.
- **Database:** SQLite (`aiosqlite`).

## ⚙️ Installation and Setup

### 1. Prerequisites

- [uv](https://github.com/astral-sh/uv) for Python dependencies.
- [bun](https://bun.sh/) for Node/Frontend dependencies.

### 2. Clone the Repository

```bash
git clone [https://github.com/rarenatoe/diplomacy-games-organizer.git](https://github.com/rarenatoe/diplomacy-games-organizer.git)
cd diplomacy-games-organizer
```

### 3. Configure Notion API Credentials

You need to connect the app to your existing Notion tracking databases.
Copy the example environment file:

```bash
cp .env.example .env
```

**How to get your Notion keys:**

1. **`NOTION_TOKEN`**: Go to [Notion My Integrations](https://www.notion.so/my-integrations). Create a "New integration" (or select an existing one) and copy the "Internal Integration Secret".
2. **`NOTION_PLAYERS_DB_ID` (Players Table)**: Open your Players database as a full page in your web browser. Look at the URL: `https://www.notion.so/workspace/{DATABASE_ID}?v=...`. The 32-character alphanumeric string before `?v=` is your ID.
3. **`NOTION_PARTICIPACIONES_DB_ID` (Participations Table)**: Follow the same URL extraction method for your Participations database.

> ⚠️ **CRITICAL STEP:** You must share your databases with your integration! Open each database in Notion, click the `•••` menu (top right) > **Connections** > **Add connection**, and select your newly created integration.

### 4. Install Dependencies

```bash
# Backend (from the root folder)
uv sync

# Frontend
cd frontend
bun install
cd ..
```

### 5. Run in Development Mode

You will need two terminal windows running simultaneously.

**Terminal 1: Backend**

```bash
uv run uvicorn backend.main:app --reload --port 5001
```

**Terminal 2: Frontend**

```bash
cd frontend
bun run dev
```

---

## 🚑 Troubleshooting

### Issue: Frontend shows `403 Forbidden` fetching API data

If your frontend console shows a `403 Forbidden` error (especially when polling endpoints like `/api/sync/status`), it usually means Vite is proxying requests to the wrong background service.

**Cause 1: The macOS Port 5000 Conflict**
If you are on a Mac, macOS runs a background service called **AirPlay Receiver** that squats on port `5000`. If your Python backend fails to start, Vite will forward requests to AirPlay, which immediately rejects them with a `403`.

- **Fix A (Recommended):** Turn off the Mac AirPlay service. Go to macOS **System Settings > General > AirDrop & Handoff** and turn off **AirPlay Receiver**.
- **Fix B:** Change your API port. Add `API_PORT=5001` to your `.env` file, and start the backend using `--port 5001`.

**Cause 2: Vite `.env` Caching**
If you updated your `.env` file (e.g., changing the `API_PORT` or your Notion keys) but you are still getting errors, Vite might not have registered the changes.

- **Fix:** Vite only reads environment variables when the dev server starts. **You must hit `CTRL+C` to stop `bun run dev`, and start it again** to pick up any changes to your `.env` file.

### Issue: "VS Code: terminal environment injection is disabled"

This is a harmless warning from the VS Code Python extension indicating it didn't inject the `.env` into your built-in terminal. You can fix this by opening VS Code Settings (`Cmd + ,`), searching for `python.terminal.useEnvFile`, and checking the box.

---

## 🧪 Testing

The project requires symmetrical test coverage for complex use cases.

- **Backend (pytest):** `bun run test:backend` (or `uv run python -m pytest`)
- **Frontend (vitest):** `cd frontend && bun run test` or `bun run test:watch`
