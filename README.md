# Chatbot Agent & React Dashboard Proof-of-Concept

A high-fidelity, clean, and interactive proof-of-concept demonstrating a natural-language chatbot that can view and modify real SQLite database data through LLM tool-calling. Powered by a local **Gemma 4** model and an ultra-premium **Vite + React** single page application.

---

## 🌟 Highlights & Features
1. **Clickable Confirmation Buttons**: ALL modifying actions (*adding/removing hobbies, creating/cancelling events, or updating settings/profile fields*) are intercepted at the server layer, pausing execution. The React chat interface instantly renders styled **Confirm Action** and **Cancel Action** buttons so you don't have to type "Yes" or "No".
2. **Multi-Step/Chained Tool Calls**: The agent evaluates user intent and can chain multiple sequential database tool runs (e.g. adding a hobby and updating a preference card at the same time) before returning a final summary.
3. **Real-Time Live Dashboard**: A custom two-column panel showing the conversational assistant on the left and a live database visual representation (Profile, Hobbies badges, Scheduled Events, Settings grid) on the right that **automatically updates in real time** as you chat.
4. **Visual Tool Traces**: Streams collapsible terminal log outputs under the active assistant bubble, allowing users to watch the specific arguments and execution results of each tool in real time.
5. **Defensive JSON Parser**: Standardizes and extracts JSON tool call blocks when smaller models (like Gemma 4) output schemas directly inside markdown text blocks rather than the tool-calling parameters field.
6. **Streaming SSE Responses**: Streams final assistant answers token-by-token for a professional, responsive user experience.

---

## 🏗️ Architecture
- **`models.py` + `db.py`**: SQLAlchemy 2.0 database mapping models and seeding/reset logic.
- **`tools.py`**: Business tools (profile, hobbies, events, settings) with robust input validation.
- **`agent.py`**: Orchestration engine, schemas, defensive parser, and confirmation state.
- **`main.py`**: FastAPI server exposing SSE chat stream and REST state polling endpoints.
- **`frontend/`**: Beautiful **Vite + React** SPA equipped with Lucide vector icons, real-time data polling, and native streaming SSE parser.

---

## 🛠️ Step-by-Step Setup

### 1. Prerequisites
- **Python 3.11+** installed.
- **Node.js (v18+)** installed.
- **LM Studio** installed on your system.

### 2. Configure LM Studio
1. Open LM Studio and download the model **Gemma 4 Instruct** (or search for `gemma-4`).
2. Load the model.
3. Navigate to the **Local Server** tab on the left.
4. Set the port to `1235` (or matches your `.env` configuration), and click **Start Server**.
5. Keep LM Studio running in the background.

### 3. Environment Setup
Configure your database and local LLM credentials in the `.env` file in the root directory:
```ini
LM_STUDIO_BASE_URL=http://localhost:1235/v1
LM_STUDIO_API_KEY=sk-lm-w7hFBqYD:3ipj257ad3OpdcHsF2oh
LLM_MODEL_NAME=gemma-4
LLM_TEMPERATURE=0.2
DATABASE_URL=sqlite:///app.db
FASTAPI_URL=http://localhost:8000
```

### 4. Running the Servers
You need to open two terminal windows (virtual environments active in both if applicable):

#### Tab 1: Start the FastAPI Backend (Root Directory)
```bash
# Install backend requirements
pip install -r requirements.txt

# Start backend server
uvicorn main:app --reload --port 8000
```
*The database seeds automatically on startup.*

#### Tab 2: Start the React Frontend (Frontend Directory)
```bash
# Navigate to frontend folder
cd frontend

# Install Node modules (if not already done)
npm install

# Start Vite React server
npm run dev
```
*Vite will start the client interface at `http://localhost:5173`.*

---

## 💬 Try These Phrases (Stakeholder Test Guide)

Here are the step-by-step example queries to showcase the main capabilities:

### 1. Viewing State
* **Phrase**: `Show me my current profile details and list my hobbies.`
* **Expectation**: The chatbot calls `get_profile` and `list_hobbies`, displaying the collapsible tool traces in the chat, and lists your details.

### 2. Multi-Step Chained Action (Requires Confirmation)
* **Phrase**: `Add Gardening as a beginner hobby and change my theme setting to dark.`
* **Expectation**: In one turn, the agent chains two tool calls (`add_hobby` and `update_setting`). The system intercepts both actions and prompts you to confirm. Once confirmed, the dashboard updates immediately!

### 3. Modifying Action - Clickable Confirmation Buttons (Hobby Removal)
* **Phrase**: `Remove swimming from my hobbies.`
* **Expectation**: The system intercepts the request. The chat UI renders a panel with custom **Confirm Action** and **Cancel Action** buttons.
* **Confirm Click**: Click `Confirm Action`. Swimming is deleted, the dashboard updates immediately, and the assistant summarizes the deletion.
* **Cancel Click**: Alternatively, click `Cancel Action`. The tool is discarded and the hobby is kept in the database.

### 4. Modifying Action - Clickable Confirmation (Event Cancellation)
* **Phrase**: `Cancel the scheduled event with ID 2.`
* **Expectation**: The system blocks direct deletion and presents the custom confirmation panel. Click to proceed or abort.

### 5. Input Validation
* **Phrase**: `Set my theme preference to green.`
* **Expectation**: The tool functions validate inputs. The agent will execute `update_setting`, receive a fail result (`{"success": False, "message": "Theme must be 'light' or 'dark'."}`), and explain to the user why the change could not be performed.
