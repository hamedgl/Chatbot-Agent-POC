import streamlit as st
import requests
import json
import uuid
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
FASTAPI_URL = os.getenv("FASTAPI_URL", "http://localhost:8000")

# Page config
st.set_page_config(
    page_title="Tool-Calling Chatbot Demo",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Custom CSS Styling
st.markdown("""
<style>
    /* Import modern Google Font */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    /* Sleek Sidebar styling */
    .css-154zq7e {
        background-color: #0e1117;
    }
    
    /* Profile details premium card */
    .profile-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    .profile-name {
        font-size: 24px;
        font-weight: 700;
        color: #f8fafc;
        margin-bottom: 5px;
    }
    .profile-bio {
        font-size: 14px;
        color: #94a3b8;
        font-style: italic;
        margin-top: 10px;
        border-top: 1px solid #334155;
        padding-top: 10px;
    }
    .profile-item {
        font-size: 14px;
        color: #cbd5e1;
        margin-bottom: 6px;
    }
    .profile-label {
        font-weight: 600;
        color: #64748b;
    }
    
    /* Hobby badges */
    .badge {
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 600;
        display: inline-block;
    }
    .badge-beginner {
        background-color: rgba(59, 130, 246, 0.15);
        color: #60a5fa;
        border: 1px solid rgba(59, 130, 246, 0.3);
    }
    .badge-intermediate {
        background-color: rgba(245, 158, 11, 0.15);
        color: #fbbf24;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }
    .badge-advanced {
        background-color: rgba(139, 92, 246, 0.15);
        color: #a78bfa;
        border: 1px solid rgba(139, 92, 246, 0.3);
    }
    
    /* Event card */
    .event-card {
        background-color: #1e293b;
        border-left: 4px solid #6366f1;
        border-radius: 0 8px 8px 0;
        padding: 12px 16px;
        margin-bottom: 12px;
    }
    .event-title {
        font-weight: 600;
        font-size: 16px;
        color: #f1f5f9;
    }
    .event-details {
        font-size: 13px;
        color: #94a3b8;
        margin-top: 4px;
    }
    
    /* Setting list item */
    .setting-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background-color: #0f172a;
        padding: 10px 14px;
        border-radius: 8px;
        border: 1px solid #1e293b;
        margin-bottom: 8px;
    }
    .setting-key {
        font-weight: 500;
        font-size: 14px;
        color: #94a3b8;
    }
    .setting-val {
        font-weight: 600;
        font-size: 14px;
        color: #f1f5f9;
    }
    
    /* Header decoration */
    .section-header {
        font-size: 20px;
        font-weight: 700;
        margin-top: 20px;
        margin-bottom: 12px;
        color: #f8fafc;
        border-bottom: 1px solid #1e293b;
        padding-bottom: 6px;
    }
</style>
""", unsafe_allow_html=True)

# Helper to fetch data safely from backend
def get_backend_data(endpoint: str):
    try:
        res = requests.get(f"{FASTAPI_URL}{endpoint}", timeout=3)
        if res.status_code == 200:
            return res.json().get("data")
        return None
    except requests.exceptions.ConnectionError:
        return "CONNECTION_ERROR"
    except Exception:
        return None

# Load states
def load_all_dashboard_data():
    profile = get_backend_data("/api/profile")
    hobbies = get_backend_data("/api/hobbies")
    events = get_backend_data("/api/events")
    settings = get_backend_data("/api/settings")
    return profile, hobbies, events, settings

# Sidebar setup
with st.sidebar:
    st.image("https://img.icons8.com/color/120/artificial-intelligence.png", width=70)
    st.title("Gemma 3 POC")
    st.markdown("""
    **Local Agent Platform**
    
    This POC demonstrates natural language tool-calling using:
    - **FastAPI** backend orchestrating a multi-step agent loop
    - **Gemma 3 4B** via LM Studio (port 1234)
    - **SQLite** database reflecting live updates
    
    ---
    """)
    
    # Session Id management
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
        
    st.caption(f"Session: `{st.session_state.session_id[:8]}...`")
    
    # Reset Data Button
    st.markdown("### Controls")
    if st.button("🔄 Reset Demo Data", use_container_width=True):
        try:
            res = requests.post(f"{FASTAPI_URL}/api/reset", timeout=3)
            if res.status_code == 200:
                st.success("Database reset successful!")
                st.session_state.messages = []  # Clear UI history
                st.rerun()
            else:
                st.error("Failed to reset database.")
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to backend.")

# Fetch dashboard data
dashboard_state = load_all_dashboard_data()
backend_connected = True

if "CONNECTION_ERROR" in dashboard_state:
    backend_connected = False
    profile_data, hobbies_data, events_data, settings_data = None, None, None, None
else:
    profile_data, hobbies_data, events_data, settings_data = dashboard_state

# Main UI Structure
st.title("🤖 Intelligent Local Database Agent")

if not backend_connected:
    st.error("🔌 **Cannot connect to the FastAPI backend!**")
    st.markdown(f"""
    Please make sure:
    1. Your FastAPI server is running (`uvicorn main:app --reload --port 8000`).
    2. Your `.env` variables point to the correct URL (currently looking at `{FASTAPI_URL}`).
    """)
    st.stop()

# Set up message history in session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Two-column layout
col_chat, col_dash = st.columns([5, 4], gap="large")

# --- LEFT COLUMN: CHAT INTERFACE ---
with col_chat:
    st.subheader("💬 Chat Orchestrator")
    
    # Render chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            # Display any traces linked to this message first
            if msg.get("traces"):
                with st.expander("🔧 View Tool Traces", expanded=False):
                    for trace in msg["traces"]:
                        st.markdown(trace)
            st.markdown(msg["content"])
            
    # Input box
    if prompt := st.chat_input("Ask me to do something..."):
        # Render user message
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Call chat API with stream enabled
        with st.chat_message("assistant"):
            # UI components for current turn
            trace_container = st.empty()
            content_container = st.empty()
            
            traces = []
            final_text = ""
            is_pending_conf = False
            
            # Post request
            try:
                # We start a streaming request to backend
                res = requests.post(
                    f"{FASTAPI_URL}/api/chat",
                    json={"message": prompt, "session_id": st.session_state.session_id},
                    stream=True,
                    timeout=60
                )
                
                # Check for successful connection
                if res.status_code != 200:
                    st.error(f"Backend returned error code: {res.status_code}")
                else:
                    for line in res.iter_lines():
                        if not line:
                            continue
                            
                        # Parse SSE line
                        decoded_line = line.decode("utf-8")
                        try:
                            event = json.loads(decoded_line)
                            
                            if event["type"] == "trace":
                                traces.append(event["message"])
                                # Render updated traces list
                                with trace_container:
                                    with st.expander("🔧 Executing Tools...", expanded=True):
                                        for t in traces:
                                            st.markdown(t)
                                            
                            elif event["type"] == "confirmation":
                                is_pending_conf = True
                                final_text = event["message"]
                                content_container.markdown(final_text)
                                
                            elif event["type"] == "content":
                                final_text += event["delta"]
                                content_container.markdown(final_text + "▌")
                                
                            elif event["type"] == "error":
                                st.error(event["message"])
                                final_text = f"Error: {event['message']}"
                                content_container.markdown(final_text)
                                
                            elif event["type"] == "done":
                                content_container.markdown(final_text)
                                
                        except json.JSONDecodeError:
                            logger.error(f"Malformed SSE JSON: {decoded_line}")
                            
            except requests.exceptions.ConnectionError:
                st.error("🔌 Connection to FastAPI server lost mid-stream!")
                final_text = "Error: Connection lost."
                
            # After turn completes, collapse the tool expander
            if traces:
                with trace_container:
                    with st.expander("🔧 View Tool Traces", expanded=False):
                        for t in traces:
                            st.markdown(t)
                            
            # Add assistant message to history
            st.session_state.messages.append({
                "role": "assistant",
                "content": final_text,
                "traces": traces if traces else None
            })
            
            # Auto refresh the dashboard by reloading the page
            st.rerun()

# --- RIGHT COLUMN: LIVE DATA DASHBOARD ---
with col_dash:
    st.subheader("📊 Live Application Data")
    
    # 1. Profile Section
    st.markdown('<div class="section-header">👤 User Profile</div>', unsafe_allow_html=True)
    if profile_data:
        st.markdown(f"""
        <div class="profile-card">
            <div class="profile-name">{profile_data.get('name', 'N/A')}</div>
            <div class="profile-item"><span class="profile-label">Email:</span> {profile_data.get('email', 'N/A')}</div>
            <div class="profile-item"><span class="profile-label">Phone:</span> {profile_data.get('phone', 'N/A')}</div>
            <div class="profile-item"><span class="profile-label">DOB:</span> {profile_data.get('dob', 'N/A')}</div>
            <div class="profile-bio">{profile_data.get('bio', 'N/A')}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("No profile loaded.")
        
    # 2. Hobbies Section
    st.markdown('<div class="section-header">🎨 Hobbies & Skill Levels</div>', unsafe_allow_html=True)
    if hobbies_data:
        # Display hobbies inside grid columns or styled list
        for h in hobbies_data:
            skill = h.get("skill_level", "beginner").lower()
            badge_class = f"badge-{skill}"
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; align-items: center; background-color: #1e293b; padding: 10px 14px; border-radius: 8px; margin-bottom: 8px;">
                <span style="font-weight: 500; color: #f1f5f9;">{h.get('name')}</span>
                <span class="badge {badge_class}">{skill.capitalize()}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No hobbies recorded.")
        
    # 3. Scheduled Events Section
    st.markdown('<div class="section-header">📅 Scheduled Events</div>', unsafe_allow_html=True)
    if events_data:
        for e in events_data:
            st.markdown(f"""
            <div class="event-card">
                <div class="event-title">{e.get('title')} <span style="font-size: 11px; color:#6366f1; float:right;">ID: {e.get('id')}</span></div>
                <div class="event-details">📍 {e.get('location')} | 📅 {e.get('date')}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No events scheduled.")
        
    # 4. Settings Section
    st.markdown('<div class="section-header">⚙️ System Preferences</div>', unsafe_allow_html=True)
    if settings_data:
        # Theme
        theme = settings_data.get("theme", "light")
        st.markdown(f"""
        <div class="setting-item">
            <span class="setting-key">Theme Accent</span>
            <span class="setting-val" style="color: {'#fbbf24' if theme == 'light' else '#60a5fa'}">
                {'☀️ Light' if theme == 'light' else '🌙 Dark'}
            </span>
        </div>
        """, unsafe_allow_html=True)
        
        # Language
        lang = settings_data.get("language", "English")
        st.markdown(f"""
        <div class="setting-item">
            <span class="setting-key">Language</span>
            <span class="setting-val">🌐 {lang}</span>
        </div>
        """, unsafe_allow_html=True)
        
        # Notifications
        notif = settings_data.get("notifications", "on")
        st.markdown(f"""
        <div class="setting-item">
            <span class="setting-key">Notifications</span>
            <span class="setting-val" style="color: {'#34d399' if notif == 'on' else '#f87171'}">
                {'🔔 On' if notif == 'on' else '🔕 Off'}
            </span>
        </div>
        """, unsafe_allow_html=True)
        
        # Timezone
        tz = settings_data.get("timezone", "America/New_York")
        st.markdown(f"""
        <div class="setting-item">
            <span class="setting-key">Timezone</span>
            <span class="setting-val">🕒 {tz}</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("No settings available.")
