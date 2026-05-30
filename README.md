# AI Agent Chatbot — Proof of Concept

A full-stack, tool-calling AI chatbot that lets you manage a personal database through plain English. Powered by a local **Gemma 4** model running in LM Studio, a **FastAPI** backend with real-time SSE streaming, a **SQLite** database, and a dark-themed **React + Vite** SPA.

---

## Features

| Feature | Detail |
|---|---|
| **Natural-language CRUD** | Read and write profile, hobbies, calendar events, and settings via conversation |
| **Streaming responses** | Word-by-word typewriter effect delivered over Server-Sent Events |
| **Confirmation gate** | Every write action is intercepted before execution — Confirm / Cancel buttons appear inline |
| **Multi-action batching** | When the LLM requests several writes in one turn, all are shown together in a single "confirm all?" prompt |
| **Persistent chat history** | Conversations are saved to SQLite and restored on page refresh or server restart |
| **Session browser** | Sidebar lists all past sessions with relative timestamps and first-message previews |
| **Session switching** | Click any past session to load it; "+ New" button starts a fresh conversation |
| **Live dashboard** | Right panel shows the current DB state (profile, hobbies, events, settings) and updates automatically after each chat turn |
| **Markdown rendering** | Agent responses render bold text, bullet lists, and inline code correctly |
| **Tool execution traces** | Collapsible terminal log under each message shows every tool call and its result |
| **Fallback tool-call parser** | Captures tool calls that Gemma leaks as raw text tokens instead of the structured `tool_calls` field |
| **Relative date resolution** | "tomorrow", "next Friday" etc. are resolved to `YYYY-MM-DD` before writing |
| **Text-to-speech** | Optional voice-output toggle in the chat header |
| **Rate limiting** | 15 requests / minute per session |
| **Demo reset** | One button wipes the DB and all chat history, then re-seeds with sample data |

---

## Architecture

```
Browser  (React + Vite · localhost:5173)
  │
  ├─ POST /api/chat  ──────────────────────────────────────────────────────►
  │  ◄── SSE stream  (trace | content | confirmation | error | done) ──────
  │
  ├─ GET  /api/profile | /api/hobbies | /api/events | /api/settings
  ├─ GET  /api/sessions                  ← sidebar history list
  ├─ GET  /api/history/{session_id}      ← restore a conversation
  └─ POST /api/reset

FastAPI server  (main.py · localhost:8000)
  └─ run_agent_loop  (agent.py)
        ├─ SessionState — per-session conversation context (in-memory)
        │       Loaded from DB on first access → survives server restarts
        ├─ Single streaming LLM call per iteration
        │       LM Studio  ←→  Gemma 4  (OpenAI-compatible API · :1234)
        ├─ Tool execution  (tools.py)
        │       get_profile    update_profile
        │       list_hobbies   add_hobby     remove_hobby
        │       list_events    create_event  cancel_event
        │       get_settings   update_setting
        └─ SQLAlchemy + SQLite  (models.py / db.py)
                profiles | hobbies | events | settings | chat_messages
```

### Key design decisions

| Decision | Reason |
|---|---|
| Single streaming LLM call | Eliminates the double-call pattern (one probe call + one streaming call) — halves latency and LM Studio load |
| Pre-classify writes before touching history | Validation and destructive-action checks happen before any messages are appended, preventing orphaned tool-call entries on failure |
| `pending_actions` queue | Supports batching multiple write operations into one confirmation prompt |
| DB-persisted chat history | `chat_messages` stores user/assistant turns; `get_or_create_session` loads them on first access |
| History trimming | System prompt + last 40 messages are sent per LLM call to stay within the model's context window |
| Rate-limiter key pruning | Dead session keys are deleted once their timestamp list empties, preventing unbounded memory growth |

---

## Prerequisites

| Tool | Notes |
|---|---|
| Python 3.11+ | |
| Node.js 18+ | |
| [LM Studio](https://lmstudio.ai) | Free desktop app — runs the local LLM server |
| Gemma 4 model | Download inside LM Studio |

---

## Setup

### 1. Clone and configure

```bash
git clone <repo-url>
cd "ai agent chat"
cp .env.example .env
```

`.env` defaults (work out of the box with LM Studio on port 1234):

```ini
LM_STUDIO_BASE_URL=http://localhost:1234/v1
LM_STUDIO_API_KEY=lm-studio
LLM_MODEL_NAME=google/gemma-4-e4b
LLM_TEMPERATURE=0.2
DATABASE_URL=sqlite:///app.db
```

### 2. LM Studio

1. Open LM Studio and download **Gemma 4** (search `gemma-4`).
2. Load the model.
3. Go to **Local Server** → set port to **1234** → **Start Server**.

### 3. Backend

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The server creates all database tables and seeds mock data on first run.

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

---

## Project structure

```
ai agent chat/
├── main.py           FastAPI app — rate limiting, SSE chat, REST, history endpoints
├── agent.py          LLM orchestration loop, session state, DB persistence, tool dispatch
├── tools.py          CRUD tool implementations with input validation
├── models.py         SQLAlchemy models (Profile, Hobby, Event, Setting, ChatMessage)
├── db.py             Engine, session factory, seed/reset helpers
├── requirements.txt
├── .env.example
└── frontend/
    └── src/
        ├── App.jsx                 Root — session management, SSE handling, layout
        ├── components/
        │   ├── Chat.jsx            Chat panel, streaming, markdown, confirmation UI
        │   ├── ChatHistory.jsx     Sidebar session browser with session switching
        │   └── Dashboard.jsx       Live profile/hobbies/events/settings panel
        └── index.css               All styles — dark theme, markdown, history panel
```

---

## API reference

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/chat` | Send a message; returns SSE stream |
| `GET` | `/api/profile` | Current profile |
| `GET` | `/api/hobbies` | Hobby list |
| `GET` | `/api/events` | Scheduled events |
| `GET` | `/api/settings` | Settings key-value map |
| `GET` | `/api/sessions` | All sessions — preview, timestamps, message count |
| `GET` | `/api/history/{session_id}` | Full ordered message history for a session |
| `POST` | `/api/reset` | Wipe DB + chat history, re-seed, clear in-memory sessions |

### SSE event schema

```jsonc
{ "type": "trace",        "message": "🔧 LLM requested tool: add_hobby({...})" }
{ "type": "content",      "delta": "word " }            // streamed word by word
{ "type": "confirmation", "message": "...", "pending": true }
{ "type": "error",        "message": "..." }
{ "type": "done" }
```

---

## Agent loop — step by step

1. **Session restore** — `get_or_create_session(session_id, db)` checks the in-memory dict first; if missing (new session or server restart), it loads all saved `chat_messages` rows for that session ID into a fresh `SessionState`.
2. **Confirmation check** — if a `pending_actions` queue exists, the user's reply is classified as affirmative / negative / ambiguous before the LLM is called.
3. **Single streaming call** — `stream=True` is passed; content chunks and tool-call deltas are accumulated together. No second call is made.
4. **Fallback parser** — if `delta.tool_calls` arrives empty but content contains Gemma's raw tool tokens or a JSON code block, the fallback regex parser normalises them.
5. **Validation** — required parameters are checked for every tool call *before* anything is written to session history.
6. **Pre-classification** — tool calls are split into safe reads and destructive writes.
7. **Reads execute immediately** — results are appended to history; loop continues.
8. **Writes are queued** — all destructive calls go into `pending_actions`; a combined confirmation message is yielded to the client.
9. **On confirm** — all queued actions execute in order; results are appended; the loop continues so the LLM summarises what happened.
10. **DB persistence** — every user turn and final assistant response is written to `chat_messages` via `save_message()`.
11. **History trim** — `trim_history()` sends only `system prompt + last 40 messages` to the LLM per call.

---

## Example walkthrough

```
You:   Add yoga at beginner level and cancel event 2.

Agent: Almost done! I need your permission to perform 2 actions:
       • add the hobby yoga (beginner)
       • cancel the scheduled event with ID 2
       Do all of these look good to you?

       [Confirm Action]  [Cancel Action]

You:   (click Confirm)

Agent: ✅ Done! I've added Yoga as a beginner hobby and cancelled
       the Weekly Team Sync event. Your dashboard has been updated.
```

---

## Seed data

The database is pre-populated on the first run (and after every reset):

| Entity | Values |
|---|---|
| Profile | Alice Smith · 1995-06-15 · alice@example.com · +1-555-0199 |
| Hobbies | Swimming (intermediate) · Reading (advanced) · Cooking (beginner) |
| Events | Tech Conference 2026-06-10 (San Francisco) · Weekly Team Sync 2026-06-03 (Zoom) |
| Settings | theme: light · language: English · notifications: on · timezone: America/New_York |
