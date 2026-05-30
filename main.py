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

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("main")

app = FastAPI(title="Tool-Calling Chatbot API Proof-of-Concept")

# Enable CORS for frontend flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    """Run database migration and seed data on server start."""
    logger.info("Initializing database and seeding mock data...")
    with next(db.get_db()) as session:
        db.seed_db(session)
    logger.info("Database initialized successfully.")

# --- RATE LIMITING ---
request_counts = defaultdict(list)
RATE_LIMIT = 15  # Max 15 requests per minute per session

async def rate_limiter(request: Request, payload: dict = Body(..., example={"message": "hello", "session_id": "session123"})):
    session_id = payload.get("session_id")
    client_ip = request.client.host if request.client else "unknown"
    identifier = session_id if session_id else client_ip
    
    current_time = time.time()
    recent = [t for t in request_counts[identifier] if current_time - t < 60]
    if recent:
        request_counts[identifier] = recent
    else:
        del request_counts[identifier]  # prune dead keys to prevent unbounded growth
        recent = []

    if len(recent) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded (15 req/min). Please slow down.")
        
    request_counts[identifier].append(current_time)  # safe: defaultdict recreates the key
    return payload

# --- CHAT ENDPOINT ---

@app.post("/api/chat")
async def chat_endpoint(
    payload: dict = Depends(rate_limiter)
):
    """
    Orchestrated chat endpoint. Processes the user message, coordinates the agent loop,
    and returns a Server-Sent Events (SSE) stream.
    """
    message = payload.get("message")
    session_id = payload.get("session_id")
    
    if not session_id:
        raise HTTPException(status_code=400, detail="Missing required field 'session_id'.")
        
    def event_generator():
        # Get fresh database session for the duration of the generator
        db_session = next(db.get_db())
        try:
            for line in run_agent_loop(db_session, session_id, message):
                yield line
        except Exception as e:
            logger.error(f"Error in chat event generator: {str(e)}", exc_info=True)
            yield f'{{"type": "error", "message": "An internal server error occurred: {str(e)}"}}\n'
        finally:
            db_session.close()
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

# --- REST ENDPOINTS (for the live dashboard) ---

@app.get("/api/profile")
def get_profile_endpoint(session: Session = Depends(db.get_db)):
    """Fetch current user profile data."""
    res = tools.get_profile(session)
    if not res["success"]:
        raise HTTPException(status_code=404, detail=res["message"])
    return res

@app.get("/api/hobbies")
def get_hobbies_endpoint(session: Session = Depends(db.get_db)):
    """Fetch current list of hobbies."""
    res = tools.list_hobbies(session)
    if not res["success"]:
        raise HTTPException(status_code=500, detail=res["message"])
    return res

@app.get("/api/events")
def get_events_endpoint(session: Session = Depends(db.get_db)):
    """Fetch current scheduled events."""
    res = tools.list_events(session)
    if not res["success"]:
        raise HTTPException(status_code=500, detail=res["message"])
    return res

@app.get("/api/settings")
def get_settings_endpoint(session: Session = Depends(db.get_db)):
    """Fetch current user preferences and settings."""
    res = tools.get_settings(session)
    if not res["success"]:
        raise HTTPException(status_code=500, detail=res["message"])
    return res

@app.post("/api/reset")
def reset_database_endpoint():
    """Reset the SQLite database to seed state and clear all in-memory sessions."""
    try:
        db.reset_db()
        clear_all_sessions()
        return {"success": True, "message": "Database wiped and re-seeded successfully."}
    except Exception as e:
        logger.error(f"Failed to reset database: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database reset failed: {str(e)}")

# --- CHAT HISTORY ENDPOINTS ---

@app.get("/api/sessions")
def get_sessions_endpoint(session: Session = Depends(db.get_db)):
    """List all chat sessions with their last-active time and first-message preview."""
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
        first_user_msg = (
            session.query(ChatMessage)
            .filter(ChatMessage.session_id == row.session_id, ChatMessage.role == "user")
            .order_by(ChatMessage.id)
            .first()
        )
        preview = ""
        if first_user_msg:
            preview = first_user_msg.content[:60] + ("…" if len(first_user_msg.content) > 60 else "")
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
    """Return the full message history for a given session."""
    messages = (
        session.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.id)
        .all()
    )
    return {
        "success": True,
        "data": [
            {"role": m.role, "content": m.content, "created_at": m.created_at}
            for m in messages
        ],
    }
