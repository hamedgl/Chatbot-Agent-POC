from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import logging

import db
import tools
from agent import run_agent_loop

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

# --- CHAT ENDPOINT ---

@app.post("/api/chat")
async def chat_endpoint(
    payload: dict = Body(..., example={"message": "hello", "session_id": "session123"})
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
    """Reset the SQLite database to seed state."""
    try:
        db.reset_db()
        return {"success": True, "message": "Database wiped and re-seeded successfully."}
    except Exception as e:
        logger.error(f"Failed to reset database: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database reset failed: {str(e)}")
