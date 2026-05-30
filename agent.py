import os
import json
import re
import logging
from typing import Dict, List, Any, Optional, Tuple, Generator
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
from sqlalchemy.orm import Session

import tools
from models import ChatMessage

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("agent")

load_dotenv()

# Configurable environment variables
LM_STUDIO_BASE_URL = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
LM_STUDIO_API_KEY = os.getenv("LM_STUDIO_API_KEY", "lm-studio")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "google/gemma-4-e4b")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))

MAX_HISTORY_MESSAGES = 40  # system prompt + last 40 messages kept per session

# Initialize LLM Client
def get_llm_client() -> OpenAI:
    return OpenAI(base_url=LM_STUDIO_BASE_URL, api_key=LM_STUDIO_API_KEY)

# Define Tool Schemas for Gemma tool-calling
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_profile",
            "description": "Get the user's profile details including name, date of birth (dob), email, phone, and bio.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_profile",
            "description": "Update a specific field of the user's profile. Empty value or empty string represent wiping/clearing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "field": {
                        "type": "string",
                        "description": "The profile field to update. Must be one of: 'name', 'dob', 'email', 'phone', 'bio'."
                    },
                    "value": {
                        "type": "string",
                        "description": "The new value for the field. An empty string '' clears/wipes the field."
                    }
                },
                "required": ["field", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_hobbies",
            "description": "Get the list of all hobbies and their corresponding skill levels (beginner, intermediate, advanced).",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_hobby",
            "description": "Add a new hobby with a skill level. If hobby already exists, updates its skill level.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the hobby (e.g. Gardening, Chess)."
                    },
                    "skill_level": {
                        "type": "string",
                        "description": "Skill level. Must be 'beginner', 'intermediate', or 'advanced'."
                    }
                },
                "required": ["name", "skill_level"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remove_hobby",
            "description": "Delete/remove a hobby from the user's list. This is a destructive action.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the hobby to remove."
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_events",
            "description": "Retrieve the list of all scheduled events including their ID, title, date (YYYY-MM-DD), and location.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_event",
            "description": "Create/schedule a new event.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Title of the event (e.g. Team lunch, Coding Club)."
                    },
                    "date": {
                        "type": "string",
                        "description": "Date of the event in YYYY-MM-DD format."
                    },
                    "location": {
                        "type": "string",
                        "description": "Location or platform for the event."
                    }
                },
                "required": ["title", "date", "location"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_event",
            "description": "Cancel and delete a scheduled event by its ID. This is a destructive action.",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "integer",
                        "description": "The ID number of the event to cancel."
                    }
                },
                "required": ["event_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_settings",
            "description": "Get current preferences/settings including theme, language, notifications, and timezone.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_setting",
            "description": "Update the value of a specific setting key.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "The settings key. Must be one of: 'theme', 'language', 'notifications', 'timezone'."
                    },
                    "value": {
                        "type": "string",
                        "description": "The value to set. For 'theme' it must be 'light' or 'dark'. For 'notifications' it must be 'on' or 'off'."
                    }
                },
                "required": ["key", "value"]
            }
        }
    }
]

SYSTEM_PROMPT = """You are a helpful and professional chatbot that manages the user's data!
You have access to a database of tool functions to interact with the user's data.

Core Capabilities:
- Profile: retrieve details, update name, dob, email, phone, bio.
- Hobbies: list hobbies, add a hobby (beginner/intermediate/advanced), remove a hobby.
- Events: list events, create a scheduled event (title, date YYYY-MM-DD, location), cancel an event.
- Settings: get current preferences, update settings (theme, language, notifications, timezone).

CRITICAL RULES:
1. Use a few relevant emojis to be friendly, but don't overdo it. Keep your answers concise and fast.
2. ALWAYS confirm back to the user what changed after performing any write action.
3. For ALL actions that change data, the system will intercept the action and require explicit user confirmation.
4. Be friendly and conversational, but highly structured.
5. If a user request is ambiguous, ask clarifying questions before calling a tool.
6. Proactively interpret user sentiment and implicit statements as request updates. For example, if the user says "I hate reading", proactively call the `remove_hobby` tool for reading!
"""

# Required parameters per tool — validated before any history modification
REQUIRED_PARAMS: Dict[str, List[str]] = {
    "add_hobby": ["name", "skill_level"],
    "create_event": ["title", "date", "location"],
    "update_profile": ["field", "value"],
    "update_setting": ["key", "value"]
}


class SessionState:
    """Manages conversation history and pending destructive action queue."""
    def __init__(self):
        self.messages: List[Dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        self.pending_actions: List[Dict[str, Any]] = []  # Queue of unconfirmed destructive calls


# Server-side sessions dictionary
sessions: Dict[str, SessionState] = {}


def get_or_create_session(session_id: str, db: Optional[Session] = None) -> SessionState:
    """
    Return existing in-memory session or create a new one.
    If db is provided and the session is new, pre-loads saved history from the database
    so conversations survive server restarts.
    """
    if session_id not in sessions:
        new_session = SessionState()
        if db is not None:
            saved = (
                db.query(ChatMessage)
                .filter(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.id)
                .all()
            )
            for row in saved:
                new_session.messages.append({"role": row.role, "content": row.content})
        sessions[session_id] = new_session
    return sessions[session_id]


def clear_all_sessions() -> None:
    sessions.clear()


def save_message(db: Session, session_id: str, role: str, content: str) -> None:
    """Persist a user or assistant message to the database."""
    try:
        db.add(ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            created_at=datetime.now().isoformat()
        ))
        db.commit()
    except Exception as e:
        logger.error(f"Failed to persist chat message: {e}")
        db.rollback()


def trim_history(messages: List[Dict]) -> List[Dict]:
    """Keep system prompt + last MAX_HISTORY_MESSAGES messages to stay within context limits."""
    if len(messages) <= MAX_HISTORY_MESSAGES + 1:
        return messages
    return [messages[0]] + messages[-MAX_HISTORY_MESSAGES:]


def normalize_tool_name(name: str) -> str:
    """Normalize and map prefixed namespaces or hallucinated tool names to correct tool names."""
    clean_name = name.lower().strip()
    clean_name = re.sub(r'^(events|hobbies|profile|settings|user|profile_tools|event_tools|hobby_tools|setting_tools)\.', '', clean_name)

    alias_map = {
        "create_scheduled_event": "create_event",
        "cancel_scheduled_event": "cancel_event",
        "delete_hobby": "remove_hobby",
        "delete_event": "cancel_event",
        "get_user_profile": "get_profile",
        "update_user_profile": "update_profile",
        "edit_profile": "update_profile"
    }

    mapped_name = alias_map.get(clean_name, clean_name)
    logger.info(f"Tool Name Normalizer: mapped '{name}' -> '{mapped_name}'")
    return mapped_name


def is_destructive_action(name: str, arguments: dict) -> Tuple[bool, str]:
    """Check if a tool call writes data and requires user confirmation."""
    if name == "remove_hobby":
        return True, f"remove your hobby of **{arguments.get('name')}**"
    if name == "add_hobby":
        return True, f"add the hobby **{arguments.get('name')}** ({arguments.get('skill_level')})"
    if name == "cancel_event":
        return True, f"cancel the scheduled event with ID **{arguments.get('event_id')}**"
    if name == "create_event":
        return True, f"schedule a new event: **{arguments.get('title')}** on {arguments.get('date')} at {arguments.get('location')}"
    if name == "update_profile":
        field = arguments.get("field", "").lower().strip()
        val = str(arguments.get("value", "")).strip()
        if val in ["", "None", "null"]:
            return True, f"clear/wipe your profile field: **{field}**"
        return True, f"update your profile **{field}** to **{val}**"
    if name == "update_setting":
        return True, f"change your **{arguments.get('key')}** setting to **{arguments.get('value')}**"
    return False, ""


def validate_tool_call(name: str, arguments: dict) -> Optional[str]:
    """Returns a user-facing error message if required params are missing, else None."""
    if name not in REQUIRED_PARAMS:
        return None
    missing = [p for p in REQUIRED_PARAMS[name] if p not in arguments or str(arguments[p]).strip() == ""]
    if not missing:
        return None

    if name == "add_hobby":
        if "name" in missing:
            return "I see you want to add a hobby, but I'm missing the hobby's name. Could you please tell me what hobby you'd like to add?"
        return f"I see you want to add **{arguments.get('name')}** as a hobby, but I need to know your skill level. Are you a **beginner**, **intermediate**, or **advanced**?"
    if name == "create_event":
        if "title" in missing:
            return "I see you want to schedule an event, but I'm missing the event's title. What is the title of the event?"
        return f"I would love to schedule the event **{arguments.get('title', 'event')}**, but I'm missing: **{', '.join(missing)}**. Please provide them."
    return f"I see you want to update your details, but I'm missing the required **{', '.join(missing)}** parameter(s). Please specify them."


def parse_fallback_tool_calls(text: str) -> List[Dict[str, Any]]:
    """
    Defensive parser: scan text content for JSON tool calls.
    Used as a fallback when the model outputs tool calls in text rather than the tool_calls API field.
    """
    if not text:
        return []

    # 1. Catch Gemma 4 raw token leaks
    gemma_matches = re.findall(r"<\|tool_call\|?>call:([a-zA-Z0-9_]+)(\{.*?\})(?:<tool_call\|?>|</tool_call>|<\|/tool_call\|>|$)", text, re.DOTALL)
    for func_name, args_str in gemma_matches:
        clean_args = args_str.replace('<|"|>', '"').replace('<|' + '"' + '|>', '"')
        clean_args = re.sub(r'(?<!")([a-zA-Z0-9_]+)\s*:', r'"\1":', clean_args)
        try:
            parsed_args = json.loads(clean_args)
            logger.info(f"Fallback Parser: Intercepted raw Gemma tool tokens for '{func_name}'")
            return [{
                "id": f"fallback_{int(datetime.now().timestamp())}",
                "type": "function",
                "function": {"name": func_name, "arguments": json.dumps(parsed_args)}
            }]
        except json.JSONDecodeError as e:
            logger.warning(f"Fallback Parser: Failed to decode Gemma args '{clean_args}': {e}")
            continue

    # 2. Search for markdown code blocks containing JSON
    json_blocks = re.findall(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if not json_blocks:
        json_blocks = re.findall(r"(\[.*?\]|\{.*?\})", text, re.DOTALL)

    for block in json_blocks:
        try:
            parsed = json.loads(block.strip())
            if isinstance(parsed, dict):
                parsed = [parsed]

            tool_calls = []
            for item in parsed:
                if "name" in item:
                    args = item.get("arguments", item.get("args", {}))
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            args = {}
                    tool_calls.append({
                        "id": f"fallback_{int(datetime.now().timestamp())}",
                        "type": "function",
                        "function": {"name": item["name"], "arguments": json.dumps(args)}
                    })

            if tool_calls:
                logger.info(f"Fallback Parser: Parsed tool calls from text: {tool_calls}")
                return tool_calls
        except json.JSONDecodeError:
            continue

    return []


def execute_tool(db: Session, name: str, arguments: dict) -> dict:
    """Execute a tool function dynamically by name."""
    try:
        if name == "get_profile":
            return tools.get_profile(db)
        elif name == "update_profile":
            return tools.update_profile(db, field=arguments.get("field"), value=arguments.get("value"))
        elif name == "list_hobbies":
            return tools.list_hobbies(db)
        elif name == "add_hobby":
            return tools.add_hobby(db, name=arguments.get("name"), skill_level=arguments.get("skill_level"))
        elif name == "remove_hobby":
            return tools.remove_hobby(db, name=arguments.get("name"))
        elif name == "list_events":
            return tools.list_events(db)
        elif name == "create_event":
            return tools.create_event(db, title=arguments.get("title"), date=arguments.get("date"), location=arguments.get("location"))
        elif name == "cancel_event":
            return tools.cancel_event(db, event_id=arguments.get("event_id"))
        elif name == "get_settings":
            return tools.get_settings(db)
        elif name == "update_setting":
            return tools.update_setting(db, key=arguments.get("key"), value=arguments.get("value"))
        else:
            return {"success": False, "message": f"Tool '{name}' is not supported."}
    except Exception as e:
        logger.error(f"Error executing tool '{name}': {str(e)}", exc_info=True)
        return {"success": False, "message": f"Execution error: {str(e)}"}


def run_agent_loop(
    db: Session,
    session_id: str,
    user_input: Optional[str] = None
) -> Generator[str, None, None]:
    """
    Main orchestration loop. Uses a single streaming LLM call per iteration,
    persists user/assistant messages to the DB, and handles multi-action confirmation queues.
    """
    session = get_or_create_session(session_id, db)
    client = get_llm_client()

    # Inject current date into system prompt each turn
    current_date_info = f"\n\nToday is {datetime.now().strftime('%A, %Y-%m-%d')}."
    if session.messages and session.messages[0]["role"] == "system":
        session.messages[0]["content"] = SYSTEM_PROMPT + current_date_info

    # 1. HANDLE CONFIRMATION FLOWS (pending_actions queue)
    if session.pending_actions and user_input:
        user_reply = user_input.lower().strip()
        affirmative_words = ["yes", "y", "confirm", "ok", "sure", "do it", "go ahead", "please do", "yep", "yeah"]
        negative_words = ["no", "n", "cancel", "stop", "dont", "don't", "abort", "nope"]
        is_confirmed = any(word in user_reply for word in affirmative_words)
        is_rejected = any(word in user_reply for word in negative_words)

        if is_confirmed:
            pending_list = session.pending_actions[:]
            session.pending_actions = []

            for p in pending_list:
                yield json.dumps({"type": "trace", "message": f"🔧 Executing confirmed action: `{p['name']}({p['args']})`"}) + "\n"

            # Re-add the assistant tool-call message (all confirmed calls together)
            session.messages.append({
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": p["id"],
                        "type": "function",
                        "function": {"name": p["name"], "arguments": json.dumps(p["args"])}
                    }
                    for p in pending_list
                ]
            })

            # Execute every pending action and record results
            for pending in pending_list:
                result = execute_tool(db, pending["name"], pending["args"])
                success_emoji = "✅" if result.get("success") else "❌"
                yield json.dumps({"type": "trace", "message": f"{success_emoji} Tool `{pending['name']}` result: `{result.get('message')}`"}) + "\n"
                session.messages.append({
                    "role": "tool",
                    "tool_call_id": pending["id"],
                    "name": pending["name"],
                    "content": json.dumps(result)
                })

            session.messages.append({"role": "user", "content": user_input})
            save_message(db, session_id, "user", user_input)
            # Fall through to agent loop so LLM generates the final summary response

        elif is_rejected:
            pending_list = session.pending_actions[:]
            session.pending_actions = []

            cancel_msg = (
                f"Okay, I have cancelled the request to {pending_list[0]['reason']}."
                if len(pending_list) == 1
                else f"Okay, I have cancelled all {len(pending_list)} pending actions."
            )
            session.messages.append({"role": "user", "content": user_input})
            save_message(db, session_id, "user", user_input)
            session.messages.append({"role": "assistant", "content": cancel_msg})
            save_message(db, session_id, "assistant", cancel_msg)

            yield json.dumps({"type": "trace", "message": f"🚫 Cancelled {len(pending_list)} pending action(s)"}) + "\n"
            yield json.dumps({"type": "content", "delta": cancel_msg}) + "\n"
            yield json.dumps({"type": "done"}) + "\n"
            return

        else:
            # Ambiguous input — re-prompt
            count = len(session.pending_actions)
            msg = f"I still have {count} pending action(s) awaiting confirmation. Please answer **Yes** or **No**."
            yield json.dumps({"type": "confirmation", "message": msg, "pending": True}) + "\n"
            yield json.dumps({"type": "done"}) + "\n"
            return

    elif user_input:
        session.messages.append({"role": "user", "content": user_input})
        save_message(db, session_id, "user", user_input)

    # 2. RUN LLM ORCHESTRATION LOOP — single streaming call per iteration
    max_iterations = 6
    iteration = 0

    while iteration < max_iterations:
        iteration += 1

        try:
            stream = client.chat.completions.create(
                model=LLM_MODEL_NAME,
                messages=trim_history(session.messages),
                tools=TOOL_SCHEMAS,
                temperature=LLM_TEMPERATURE,
                stream=True
            )
        except Exception as e:
            logger.error(f"Error calling LM Studio: {str(e)}")
            yield json.dumps({
                "type": "error",
                "message": "Unable to reach LM Studio. Please make sure the LM Studio server is running locally on port 1234 and the API is turned on."
            }) + "\n"
            return

        # Accumulate the full streamed response (content + tool call deltas)
        content_parts: List[str] = []
        tool_call_chunks: Dict[int, Dict] = {}

        try:
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta

                if delta.content:
                    content_parts.append(delta.content)

                if delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        idx = tc_delta.index
                        if idx not in tool_call_chunks:
                            tool_call_chunks[idx] = {
                                "id": f"tc_{idx}_{int(datetime.now().timestamp() * 1000)}",
                                "type": "function",
                                "function": {"name": "", "arguments": ""}
                            }
                        if tc_delta.id:
                            tool_call_chunks[idx]["id"] = tc_delta.id
                        if tc_delta.function:
                            if tc_delta.function.name:
                                tool_call_chunks[idx]["function"]["name"] += tc_delta.function.name
                            if tc_delta.function.arguments:
                                tool_call_chunks[idx]["function"]["arguments"] += tc_delta.function.arguments
        except Exception as e:
            logger.error(f"Streaming read error: {str(e)}")
            yield json.dumps({"type": "error", "message": "Streaming error from LM Studio."}) + "\n"
            return

        content = "".join(content_parts)
        # Preserve original tool call order by index
        tool_calls = [tool_call_chunks[i] for i in sorted(tool_call_chunks.keys())] if tool_call_chunks else []

        # Fallback: detect tool calls embedded in content text (handles Gemma token leaks)
        if not tool_calls and content:
            fallback_calls = parse_fallback_tool_calls(content)
            if fallback_calls:
                logger.warning("Fallback parser intercepted tool calls from content text.")
                tool_calls = fallback_calls

        # 2a. NO TOOL CALLS — this is the final response; emit, persist, and exit
        if not tool_calls:
            if content:
                words = content.split(' ')
                for i, word in enumerate(words):
                    yield json.dumps({"type": "content", "delta": word + ('' if i == len(words) - 1 else ' ')}) + "\n"
                session.messages.append({"role": "assistant", "content": content})
                save_message(db, session_id, "assistant", content)
            yield json.dumps({"type": "done"}) + "\n"
            return

        # 2b. VALIDATE all tool calls BEFORE modifying history
        for tool_call in tool_calls:
            tc_name = normalize_tool_name(tool_call["function"]["name"])
            try:
                tc_args = json.loads(tool_call["function"]["arguments"]) if tool_call["function"]["arguments"] else {}
            except json.JSONDecodeError:
                tc_args = {}

            error_msg = validate_tool_call(tc_name, tc_args)
            if error_msg:
                yield json.dumps({"type": "trace", "message": f"⚠️ Halting: Missing required params for `{tc_name}`"}) + "\n"
                yield json.dumps({"type": "content", "delta": error_msg}) + "\n"
                yield json.dumps({"type": "done"}) + "\n"
                session.messages.append({"role": "assistant", "content": error_msg})
                save_message(db, session_id, "assistant", error_msg)
                return

        # 2c. PRE-CLASSIFY: separate safe (read) calls from destructive (write) calls
        safe_calls: List[Dict] = []
        pending_destructive: List[Dict] = []

        for tool_call in tool_calls:
            tc_id = tool_call["id"]
            tc_name = normalize_tool_name(tool_call["function"]["name"])
            try:
                tc_args = json.loads(tool_call["function"]["arguments"]) if tool_call["function"]["arguments"] else {}
            except json.JSONDecodeError:
                tc_args = {}

            yield json.dumps({"type": "trace", "message": f"🔧 LLM requested tool: `{tc_name}({tc_args})`"}) + "\n"

            is_dest, reason = is_destructive_action(tc_name, tc_args)
            if is_dest:
                pending_destructive.append({"id": tc_id, "name": tc_name, "args": tc_args, "reason": reason})
            else:
                safe_calls.append({"id": tc_id, "name": tc_name, "args": tc_args})

        # 2d. ANY DESTRUCTIVE CALLS — queue them all and ask for confirmation
        if pending_destructive:
            session.pending_actions = pending_destructive

            if len(pending_destructive) == 1:
                confirm_msg = f"Almost done! I just need your permission to {pending_destructive[0]['reason']}. Does this look good to you?"
            else:
                reasons_str = "\n".join(f"• {a['reason']}" for a in pending_destructive)
                confirm_msg = f"Almost done! I need your permission to perform {len(pending_destructive)} actions:\n{reasons_str}\n\nDo all of these look good to you?"

            yield json.dumps({"type": "confirmation", "message": confirm_msg, "pending": True}) + "\n"
            yield json.dumps({"type": "done"}) + "\n"
            return

        # 2e. ALL SAFE — add assistant message as a plain dict and execute all tools
        session.messages.append({
            "role": "assistant",
            "content": content or "",
            "tool_calls": tool_calls
        })

        for safe in safe_calls:
            result = execute_tool(db, safe["name"], safe["args"])
            success_emoji = "✅" if result.get("success") else "❌"
            yield json.dumps({"type": "trace", "message": f"{success_emoji} Tool `{safe['name']}` result: `{result.get('message')}`"}) + "\n"
            session.messages.append({
                "role": "tool",
                "tool_call_id": safe["id"],
                "name": safe["name"],
                "content": json.dumps(result)
            })

        # Continue loop — LLM reads tool results and either calls more tools or responds

    # Exceeded max iterations
    yield json.dumps({"type": "trace", "message": "⚠️ Cap of 6 agent iterations reached. Ending agent loop."}) + "\n"
    limit_msg = "I've hit my maximum thinking iterations. Let me know what you'd like to do next."
    session.messages.append({"role": "assistant", "content": limit_msg})
    save_message(db, session_id, "assistant", limit_msg)
    yield json.dumps({"type": "content", "delta": limit_msg}) + "\n"
    yield json.dumps({"type": "done"}) + "\n"
