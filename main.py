import os
from fastapi import FastAPI, Depends, HTTPException, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
import logging
import time
from collections import defaultdict
import db
import tools
from models import ChatMessage
from agent import run_agent_loop, clear_all_sessions

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("main")

app = FastAPI(title="AI Agent Chatbot API", docs_url="/docs", redoc_url=None)

# CORS — restrict to explicit allowlist; never use * in production
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

@app.on_event("startup")
def startup_event():
    logger.info("Initializing database...")
    with next(db.get_db()) as session:
        db.seed_db(session)
    logger.info("Database ready.")

# ── Rate limiting ──────────────────────────────────────────────────────────────
request_counts: dict = defaultdict(list)
RATE_LIMIT = 15  # requests per 60 s per session

async def rate_limiter(request: Request, payload: dict = Body(...)):
    session_id = payload.get("session_id")
    identifier = session_id or (request.client.host if request.client else "unknown")

    now = time.time()
    recent = [t for t in request_counts[identifier] if now - t < 60]
    if recent:
        request_counts[identifier] = recent
    else:
        del request_counts[identifier]  # prune dead keys
        recent = []

    if len(recent) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Max 15 requests/minute.")

    request_counts[identifier].append(now)
    return payload

# ── Chat (SSE) ─────────────────────────────────────────────────────────────────

MAX_MESSAGE_LENGTH = 4_000  # characters

@app.post("/api/chat")
async def chat_endpoint(payload: dict = Depends(rate_limiter)):
    message = payload.get("message", "")
    session_id = payload.get("session_id")

    if not session_id:
        raise HTTPException(status_code=400, detail="Missing required field 'session_id'.")
    if len(message) > MAX_MESSAGE_LENGTH:
        raise HTTPException(status_code=400, detail=f"Message exceeds {MAX_MESSAGE_LENGTH} character limit.")

    def event_generator():
        db_session = next(db.get_db())
        try:
            for line in run_agent_loop(db_session, session_id, message):
                yield line
        except Exception as e:
            # Log full detail server-side; send a safe generic message to the client
            logger.error("Unhandled error in chat generator", exc_info=True)
            yield '{"type": "error", "message": "An internal server error occurred. Please try again."}\n'
        finally:
            db_session.close()

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# ── Dashboard REST endpoints ───────────────────────────────────────────────────

@app.get("/api/profile")
def get_profile_endpoint(session: Session = Depends(db.get_db)):
    res = tools.get_profile(session)
    if not res["success"]:
        raise HTTPException(status_code=404, detail=res["message"])
    return res

@app.get("/api/hobbies")
def get_hobbies_endpoint(session: Session = Depends(db.get_db)):
    res = tools.list_hobbies(session)
    if not res["success"]:
        raise HTTPException(status_code=500, detail=res["message"])
    return res

@app.get("/api/events")
def get_events_endpoint(session: Session = Depends(db.get_db)):
    res = tools.list_events(session)
    if not res["success"]:
        raise HTTPException(status_code=500, detail=res["message"])
    return res

@app.get("/api/settings")
def get_settings_endpoint(session: Session = Depends(db.get_db)):
    res = tools.get_settings(session)
    if not res["success"]:
        raise HTTPException(status_code=500, detail=res["message"])
    return res

@app.post("/api/reset")
def reset_database_endpoint():
    try:
        db.reset_db()
        clear_all_sessions()
        return {"success": True, "message": "Database wiped and re-seeded."}
    except Exception as e:
        logger.error("Database reset failed", exc_info=True)
        raise HTTPException(status_code=500, detail="Database reset failed.")

# ── Chat history endpoints ─────────────────────────────────────────────────────

@app.get("/api/sessions")
def get_sessions_endpoint(session: Session = Depends(db.get_db)):
    rows = (
        session.query(
            ChatMessage.session_id,
            func.min(ChatMessage.created_at).label("started_at"),
            func.max(ChatMessage.created_at).label("last_at"),
            func.count(ChatMessage.id).label("message_count"),
        )
        .group_by(ChatMessage.session_id)
        .order_by(func.max(ChatMessage.created_at).desc())
        .all()
    )
    result = []
    for row in rows:
        first_msg = (
            session.query(ChatMessage)
            .filter(ChatMessage.session_id == row.session_id, ChatMessage.role == "user")
            .order_by(ChatMessage.id)
            .first()
        )
        preview = ""
        if first_msg:
            preview = first_msg.content[:60] + ("…" if len(first_msg.content) > 60 else "")
        result.append({
            "session_id": row.session_id,
            "started_at": row.started_at,
            "last_at": row.last_at,
            "message_count": row.message_count,
            "preview": preview or "Empty session",
        })
    return {"success": True, "data": result}

@app.get("/api/history/{session_id}")
def get_history_endpoint(session_id: str, session: Session = Depends(db.get_db)):
    messages = (
        session.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.id)
        .all()
    )
    return {
        "success": True,
        "data": [{"role": m.role, "content": m.content, "created_at": m.created_at} for m in messages],
    }
