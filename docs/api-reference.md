# API Reference

Base URL — local: `http://localhost:8000` | AWS: `https://<cloudfront-domain>`

## Endpoints

### `POST /api/chat`

Send a user message. Returns a **Server-Sent Events** stream.

**Request body**
```json
{ "message": "Add yoga at beginner level", "session_id": "abc123" }
```

**Rate limit:** 15 requests / 60 s per session. Returns `429` when exceeded.
**Message limit:** 4 000 characters. Returns `400` when exceeded.

**SSE event types**

| `type` | Fields | Description |
|---|---|---|
| `trace` | `message` | Tool call log line (shown in collapsible panel) |
| `content` | `delta` | One word of the assistant response |
| `confirmation` | `message`, `pending: true` | Write action awaiting yes/no |
| `error` | `message` | Generic error (detail is in server logs only) |
| `done` | — | Turn complete |

**Example stream**
```
{"type":"trace","message":"🔧 LLM requested tool: add_hobby(...)"}
{"type":"confirmation","message":"Add yoga (beginner)? Confirm?","pending":true}
{"type":"done"}
```

---

### `GET /api/profile`
Returns the current user profile.

### `GET /api/hobbies`
Returns all hobbies with skill levels.

### `GET /api/events`
Returns all scheduled events ordered by date.

### `GET /api/settings`
Returns all settings as a key-value map.

### `POST /api/reset`
Wipes the database, re-seeds with mock data, and clears all in-memory sessions.

---

### `GET /api/sessions`
Lists all chat sessions.

**Response**
```json
{
  "success": true,
  "data": [
    {
      "session_id": "abc123",
      "started_at": "2026-05-30T10:00:00",
      "last_at": "2026-05-30T11:30:00",
      "message_count": 12,
      "preview": "What are my hobbies?"
    }
  ]
}
```

### `GET /api/history/{session_id}`
Returns the full message history for a session.

**Response**
```json
{
  "success": true,
  "data": [
    { "role": "user",      "content": "What are my hobbies?", "created_at": "..." },
    { "role": "assistant", "content": "You have 3 hobbies...", "created_at": "..." }
  ]
}
```
