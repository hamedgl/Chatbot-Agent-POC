# Python Tool-Calling Chatbot Proof-of-Concept

A complete, clean, and highly visual proof-of-concept demonstrating a natural-language chatbot that can view and modify real database data through LLM tool-calling capabilities. Powered by a local **Gemma 3 4B** model running via LM Studio.

---

## 🌟 Highlights & Features
1. **Robust Confirmation Flow**: Intercepts destructive actions (*removing a hobby, cancelling an event, or wiping/clearing profile fields*) at the server/orchestration layer, requiring user confirmation before execution.
2. **Multi-Step/Chained Tool Calls**: Supports complex sentences requiring the agent to call multiple tools sequentially before responding (e.g. adding a hobby and changing a setting at the same time).
3. **Real-Time Live Dashboard**: A two-column interface showing the interactive chat on the left and a live-updating view of the SQLite database data (profile, hobbies, events, and settings) on the right.
4. **Defensive JSON Parsing**: Handles smaller models (like Gemma 3 4B) that sometimes emit JSON tool calls directly in their text response block instead of the structured API field.
5. **Streaming Responses**: Streams the final natural-language assistant response chunk-by-chunk for a professional, conversational user experience.
6. **Persistent Session Memory**: Server-side conversation and tool-calling context managed per unique session ID.

---

## 🏗️ Architecture
- **`models.py` + `db.py`**: SQLAlchemy ORM definitions and SQLite seeding/reset logic.
- **`tools.py`**: The actual business functions (get/update profile, list/add/remove hobbies, list/create/cancel events, get/update settings) containing strict input validations.
- **`agent.py`**: Orchestration loop, dynamic schema definitions, defensive parser, and confirmation state machine.
- **`main.py`**: FastAPI application exposing SSE `/api/chat` streaming and REST endpoints for the live dashboard.
- **`app_ui.py`**: Premium Streamlit UI with collapsible tool traces and real-time dashboard representation.

---

## 🛠️ Step-by-Step Setup

### 1. Prerequisites
- **Python 3.11+** installed.
- **LM Studio** installed on your system.

### 2. Configure LM Studio
1. Open LM Studio and search/download the model **Gemma 3 4B Instruct** (or search for `gemma-3-4b-instruct`).
2. Load the model.
3. Navigate to the **Local Server** section on the left sidebar.
4. Set the port to `1234` and click **Start Server**.
5. Keep LM Studio running in the background.

### 3. Environment & Dependencies Setup
Clone or locate the project directory in your terminal and run:

```bash
# Create a virtual environment
python -m venv venv

# Activate virtual environment
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On macOS/Linux:
source venv/bin/activate

# Install required packages
pip install -r requirements.txt
```

Verify your environment configuration in the `.env` file (copied from `.env.example` automatically on first setup):
```ini
LM_STUDIO_BASE_URL=http://localhost:1234/v1
LM_STUDIO_API_KEY=lm-studio
LLM_MODEL_NAME=gemma-3-4b
LLM_TEMPERATURE=0.2
DATABASE_URL=sqlite:///app.db
FASTAPI_URL=http://localhost:8000
```

### 4. Running the Servers
You need to open two terminal tabs (with virtual environments activated in both):

#### Tab 1: Start the FastAPI Backend
```bash
uvicorn main:app --reload --port 8000
```
*The server will auto-seed the `app.db` file on startup.*

#### Tab 2: Start the Streamlit Frontend
```bash
streamlit run app_ui.py
```
*Streamlit will automatically launch in your browser at `http://localhost:8501`.*

---

## 💬 Try These Phrases (Test Guide)

Here are the step-by-step example queries to showcase the main capabilities to stakeholders:

### 1. Viewing & Querying State
* **Phrase**: `Show me my current profile details and list my hobbies.`
* **Expectation**: The chatbot calls `get_profile` and `list_hobbies`, displaying the collapsible tool traces in the chat, and replies with your info.

### 2. Multi-Step/Chained Action
* **Phrase**: `Add Gardening as a beginner hobby and change my theme setting to dark.`
* **Expectation**: In one turn, the agent chains two tool calls (`add_hobby` and `update_setting`). Look at the dashboard on the right: a new hobby card appears and the theme changes to dark!

### 3. Destructive Action - Confirmation Flow (Hobby Removal)
* **Phrase**: `Remove swimming from my hobbies.`
* **Expectation**: The agent pauses and prints a confirmation prompt: *"⚠️ Confirmation Required: You requested to remove your hobby of swimming. Do you want to proceed? (Yes/No)"*.
* **Next Input (Yes)**: Type `Yes`. The tool executes, swimming disappears from the dashboard, and the chatbot confirms the action.
* **Next Input (No)**: Alternatively, type `No`. The tool is discarded and no change occurs.

### 4. Destructive Action - Confirmation Flow (Event Cancellation)
* **Phrase**: `Cancel the scheduled event with ID 2.`
* **Expectation**: The system intercepts the delete request, requests approval, and only deletes the event from the database/dashboard once you confirm with an affirmative response.

### 5. Destructive Action - Confirmation Flow (Profile Wipe)
* **Phrase**: `Clear out my bio field.`
* **Expectation**: Because setting a field value to empty counts as a wipe, the system flags it as destructive and requests confirmation before emptying the text.

### 6. Dynamic Event Scheduling
* **Phrase**: `Schedule a Coding Meetup on 2026-06-15 at the Downtown Library.`
* **Expectation**: The agent schedules the event using `create_event`, and you see it populate on the live dashboard.

### 7. Input Validation & Error Handling
* **Phrase**: `Set my theme to green` or `Change my DOB to tomorrow.`
* **Expectation**: The tool functions validate inputs. The agent will execute the tool, receive a fail result (`{"success": False, "message": "Theme must be 'light' or 'dark'."}`), and explain to the user why the change could not be performed.
