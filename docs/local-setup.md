# Local Setup

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.11+ | |
| Node.js | 18+ | |
| [LM Studio](https://lmstudio.ai) | Latest | Free desktop app |
| Gemma 4 (or any model) | — | Download inside LM Studio |

## Steps

### 1. Clone and configure

```bash
git clone <repo-url>
cd "ai agent chat"
cp .env.example .env
```

The defaults in `.env.example` work out of the box. Only change values if your LM Studio runs on a different port.

### 2. Start LM Studio

1. Open LM Studio and download **Gemma 4** (search `gemma-4`)
2. Load the model
3. Go to **Local Server** → set port to **1234** → **Start Server**

### 3. Backend

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The server creates all database tables and seeds mock data on first run. You should see:

```
INFO - Initializing database...
INFO - Database ready.
INFO - Uvicorn running on http://0.0.0.0:8000
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

## Optional: Docker Compose

Run everything in containers with a single command:

```bash
# SQLite (default)
docker-compose up --build

# PostgreSQL (add --profile postgres)
POSTGRES_PASSWORD=secret docker-compose --profile postgres up --build
# Also set: DATABASE_URL=postgresql://chatbot:secret@postgres:5432/chatbot in .env
```

## Environment variables (local)

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `lmstudio` | Keep as `lmstudio` for local dev |
| `LM_STUDIO_BASE_URL` | `http://localhost:1234/v1` | LM Studio server URL |
| `LLM_MODEL_NAME` | `google/gemma-4-e4b` | Model name shown in LM Studio |
| `LLM_TEMPERATURE` | `0.2` | Lower = more deterministic |
| `DATABASE_URL` | `sqlite:///app.db` | SQLite file path |
| `ALLOWED_ORIGINS` | `http://localhost:5173` | CORS allowlist |
| `SESSION_TTL_HOURS` | `24` | Idle session eviction time |

## Resetting to seed data

Click **Reset Demo Data** in the sidebar, or hit the API directly:

```bash
curl -X POST http://localhost:8000/api/reset
```
