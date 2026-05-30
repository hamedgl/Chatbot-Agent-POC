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

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("agent")

load_dotenv()

# Configurable environment variables
LM_STUDIO_BASE_URL = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
LM_STUDIO_API_KEY = os.getenv("LM_STUDIO_API_KEY", "lm-studio")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "google/gemma-4-e4b")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))

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

SYSTEM_PROMPT = """You are a helpful, professional chatbot that reads and modifies user data on their behalf.
You have access to a database of tool functions to interact with the user's data.

Core Capabilities:
- Profile: retrieve details, update name, dob, email, phone, bio.
- Hobbies: list hobbies, add a hobby (beginner/intermediate/advanced), remove a hobby.
- Events: list events, create a scheduled event (title, date YYYY-MM-DD, location), cancel an event.
- Settings: get current preferences, update settings (theme, language, notifications, timezone).

CRITICAL RULES:
1. Always confirm back to the user what changed after performing any write action.
2. For destructive actions (removing a hobby, cancelling an event, or clearing/wiping any profile field to empty/null), the orchestration layer will intercept and require explicit confirmation. Explain to the user why you are asking for confirmation.
3. Be friendly and conversational, but highly structured.
4. If a user request is ambiguous, ask clarifying questions before calling a tool.
5. If a tool call fails or returns an error, explain the error to the user in a helpful way.
6. Proactively interpret user sentiment and implicit statements as request updates. For example, if the user says "I hate reading" or "I don't do swimming anymore", proactively call the `remove_hobby` tool for that hobby name.
7. ALWAYS use structured Markdown formatting for your responses. When listing data (like events or hobbies), use bullet points, bold text, and headers (###) to make the response highly readable and structured rather than a general text blob.
"""

class SessionState:
    """Class to manage chatbot conversation history and pending action state server-side."""
    def __init__(self):
        self.messages: List[Dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        self.pending_action: Optional[Dict[str, Any]] = None

# Server-side sessions dictionary
sessions: Dict[str, SessionState] = {}

def get_or_create_session(session_id: str) -> SessionState:
    if session_id not in sessions:
        sessions[session_id] = SessionState()
    return sessions[session_id]

def normalize_tool_name(name: str) -> str:
    """Normalize and map prefixed namespaces or hallucinated tool names to correct tool names."""
    # Lowercase and clean
    clean_name = name.lower().strip()
    
    # Remove any prefixed namespace (e.g., "events.create_event" -> "create_event")
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
    """
    Check if a tool call is destructive and requires a confirmation flow.
    Returns (is_destructive, reason_description).
    """
    if name == "remove_hobby":
        return True, f"remove your hobby of **{arguments.get('name')}**"
    
    if name == "cancel_event":
        return True, f"cancel the scheduled event with ID **{arguments.get('event_id')}**"
    
    if name == "update_profile":
        field = arguments.get("field", "").lower().strip()
        val = str(arguments.get("value", "")).strip()
        if val in ["", "None", "null"]:
            return True, f"clear/wipe your profile field: **{field}**"
            
    return False, ""

def parse_fallback_tool_calls(text: str) -> List[Dict[str, Any]]:
    """
    Defensive parser: scan text content for a JSON block (array or object) representing tool calls.
    Used as a fallback when Gemma outputs tool calls directly in text rather than the tool_calls API field.
    """
    if not text:
        return []

    # Search for markdown code blocks containing JSON
    json_blocks = re.findall(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if not json_blocks:
        # Search for raw brackets or braces if no markdown blocks are found
        json_blocks = re.findall(r"(\[.*?\]|\{.*?\})", text, re.DOTALL)

    for block in json_blocks:
        try:
            parsed = json.loads(block.strip())
            # Convert single object to list
            if isinstance(parsed, dict):
                parsed = [parsed]
            
            # Standardize tool calls list
            tool_calls = []
            for item in parsed:
                if "name" in item:
                    # Make sure the arguments are parsed or stored correctly
                    args = item.get("arguments", item.get("args", {}))
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            args = {}
                    
                    tool_calls.append({
                        "id": f"fallback_{int(datetime.now().timestamp())}",
                        "type": "function",
                        "function": {
                            "name": item["name"],
                            "arguments": json.dumps(args)
                        }
                    })
            
            if tool_calls:
                logger.info(f"Fallback Parser: Successfully parsed tool calls from text: {tool_calls}")
                return tool_calls
        except json.JSONDecodeError:
            continue
            
    return []

def execute_tool(db: Session, name: str, arguments: dict) -> dict:
    """Execute a python tool function dynamically based on name and arguments."""
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
    Main orchestration loop. Runs multi-step LLM calls, handles destructive confirmations,
    performs defensive tool call parsing, and yields SSE-friendly events streaming back to the client.
    """
    session = get_or_create_session(session_id)
    client = get_llm_client()
    
    # Dynamically inject the current system time to enable robust relative date reasoning
    current_date_info = f"\n\nToday is {datetime.now().strftime('%A, %Y-%m-%d')}."
    if session.messages and session.messages[0]["role"] == "system":
        session.messages[0]["content"] = SYSTEM_PROMPT + current_date_info
    
    # 1. HANDLE CONFIRMATION FLOWS (if there is a pending action)
    if session.pending_action and user_input:
        user_reply = user_input.lower().strip()
        
        # Affirmative keywords match
        affirmative_words = ["yes", "y", "confirm", "ok", "sure", "do it", "go ahead", "please do", "yep", "yeah"]
        negative_words = ["no", "n", "cancel", "stop", "dont", "don't", "abort", "nope"]
        
        is_confirmed = any(word in user_reply for word in affirmative_words)
        is_rejected = any(word in user_reply for word in negative_words)
        
        if is_confirmed:
            # Execute the stored pending action
            pending = session.pending_action
            session.pending_action = None # Clear pending state
            
            yield json.dumps({"type": "trace", "message": f"🔧 Executing confirmed destructive action: `{pending['name']}({pending['args']})`"}) + "\n"
            
            # Execute and record result
            result = execute_tool(db, pending["name"], pending["args"])
            
            # We append the original model assistant tool request and the tool execution result
            # to keep conversation history intact for the LLM
            session.messages.append({
                "role": "assistant",
                "content": f"Requesting destructive action: {pending['name']}",
                "tool_calls": [{
                    "id": pending["id"],
                    "type": "function",
                    "function": {
                        "name": pending["name"],
                        "arguments": json.dumps(pending["args"])
                    }
                }]
            })
            
            session.messages.append({
                "role": "tool",
                "tool_call_id": pending["id"],
                "name": pending["name"],
                "content": json.dumps(result)
            })
            
            # Fallthrough to normal agent loop so the model can generate its final response
            # we also append user's "Yes" message to history
            session.messages.append({"role": "user", "content": user_input})
            
        elif is_rejected:
            pending = session.pending_action
            session.pending_action = None # Clear
            
            yield json.dumps({"type": "trace", "message": f"🚫 Cancelled destructive action: `{pending['name']}`"}) + "\n"
            
            cancel_msg = f"Okay, I have cancelled the request to {pending['reason']}."
            session.messages.append({"role": "user", "content": user_input})
            session.messages.append({"role": "assistant", "content": cancel_msg})
            
            yield json.dumps({"type": "content", "delta": cancel_msg}) + "\n"
            yield json.dumps({"type": "done"}) + "\n"
            return
        else:
            # Ambiguous input - ask again
            pending = session.pending_action
            msg = f"I still have a pending action to {pending['reason']}. Would you like to proceed? Please answer Yes or No."
            
            yield json.dumps({"type": "confirmation", "message": msg, "pending": True}) + "\n"
            yield json.dumps({"type": "done"}) + "\n"
            return

    # Normal prompt processing
    elif user_input:
        session.messages.append({"role": "user", "content": user_input})
        
    # 2. RUN LLM ORCHESTRATION LOOP
    max_iterations = 6
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        
        try:
            # Sync call to identify tool requests
            response = client.chat.completions.create(
                model=LLM_MODEL_NAME,
                messages=session.messages,
                tools=TOOL_SCHEMAS,
                temperature=LLM_TEMPERATURE
            )
        except Exception as e:
            logger.error(f"Error calling LM Studio: {str(e)}")
            yield json.dumps({
                "type": "error", 
                "message": "Unable to reach LM Studio. Please make sure the LM Studio server is running locally on port 1234 and the API is turned on."
            }) + "\n"
            return
            
        response_message = response.choices[0].message
        content = response_message.content
        tool_calls = response_message.tool_calls
        
        # 2a. DEFENSIVE PARSING FALLBACK
        # If tool_calls field is empty but we suspect tool calls in the content text (common for small models)
        if not tool_calls and content:
            fallback_calls = parse_fallback_tool_calls(content)
            if fallback_calls:
                logger.warning("LM Studio did not populate 'tool_calls' field, but fallback parser successfully found JSON tool calls in text.")
                tool_calls = fallback_calls
        
        # 2b. IF NO TOOL CALLS, WE ARE READY TO STREAM THE FINAL RESPONSE
        if not tool_calls:
            # We will stream the final assistant response to the client
            # Let's save a placeholder in session history
            # Then perform a streaming call to get the final tokens
            try:
                stream_res = client.chat.completions.create(
                    model=LLM_MODEL_NAME,
                    messages=session.messages,
                    temperature=LLM_TEMPERATURE,
                    stream=True
                )
                
                final_content = ""
                for chunk in stream_res:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        final_content += delta
                        yield json.dumps({"type": "content", "delta": delta}) + "\n"
                
                # Append assistant final response to context history
                if final_content:
                    session.messages.append({"role": "assistant", "content": final_content})
                
                yield json.dumps({"type": "done"}) + "\n"
                return
            except Exception as e:
                # If streaming fails, fallback to using the non-streamed content we already have
                logger.error(f"Streaming failed: {str(e)}")
                if content:
                    session.messages.append({"role": "assistant", "content": content})
                    yield json.dumps({"type": "content", "delta": content}) + "\n"
                yield json.dumps({"type": "done"}) + "\n"
                return
                
        # 2c. IF THERE ARE TOOL CALLS, PROCESS THEM
        # Append assistant's intent to history
        session.messages.append(response_message)
        
        # Process each tool call in sequence
        # Note: If a tool is destructive, we halt the entire loop and ask for confirmation
        halt_for_confirmation = False
        
        for tool_call in tool_calls:
            # Standardize tool call structure depending on API / fallback structures
            if isinstance(tool_call, dict):
                # Fallback format
                tc_id = tool_call["id"]
                name = tool_call["function"]["name"]
                args_str = tool_call["function"]["arguments"]
            else:
                # OpenAI SDK object format
                tc_id = tool_call.id
                name = tool_call.function.name
                args_str = tool_call.function.arguments
                
            name = normalize_tool_name(name)
                
            try:
                arguments = json.loads(args_str) if args_str else {}
            except json.JSONDecodeError:
                arguments = {}
                
            # Validation check for missing required parameters
            required_checklist = {
                "add_hobby": ["name", "skill_level"],
                "create_event": ["title", "date", "location"],
                "update_profile": ["field", "value"],
                "update_setting": ["key", "value"]
            }
            
            if name in required_checklist:
                missing = [p for p in required_checklist[name] if p not in arguments or str(arguments[p]).strip() == ""]
                if missing:
                    # Halt execution
                    # Remove the assistant's incomplete tool-call message from history
                    session.messages.pop()
                    
                    # Formulate a premium, highly contextual message
                    if name == "add_hobby":
                        if "name" in missing:
                            msg = "I see you want to add a hobby, but I'm missing the hobby's name. Could you please tell me what hobby you'd like to add?"
                        else:
                            hobby_name = arguments.get("name", "this hobby")
                            msg = f"I see you want to add **{hobby_name}** as a hobby, but I need to know your skill level. Are you a **beginner**, **intermediate**, or **advanced**?"
                    elif name == "create_event":
                        if "title" in missing:
                            msg = "I see you want to schedule an event, but I'm missing the event's title. What is the title of the event?"
                        else:
                            title = arguments.get("title", "event")
                            msg = f"I would love to schedule the event **{title}**, but I'm missing: **{', '.join(missing)}**. Please provide them."
                    else:
                        msg = f"I see you want to update your details, but I'm missing the required **{', '.join(missing)}** parameter(s). Please specify them."
                        
                    session.messages.append({"role": "assistant", "content": msg})
                    
                    yield json.dumps({"type": "trace", "message": f"⚠️ Halting: Missing required parameters for `{name}`: {missing}"}) + "\n"
                    yield json.dumps({"type": "content", "delta": msg}) + "\n"
                    yield json.dumps({"type": "done"}) + "\n"
                    return
                
            yield json.dumps({"type": "trace", "message": f"🔧 LLM requested tool: `{name}({arguments})`"}) + "\n"
            
            # Check destructive confirmation
            is_dest, reason = is_destructive_action(name, arguments)
            if is_dest:
                # Store in session state as pending
                session.pending_action = {
                    "id": tc_id,
                    "name": name,
                    "args": arguments,
                    "reason": reason
                }
                
                # Ask user for confirmation
                confirm_prompt = f"⚠️ **Confirmation Required**: You requested to **{reason}**.\nThis is a destructive action. Do you want to proceed? (Yes/No)"
                
                # We need to remove the assistant's request from history for now,
                # since we didn't execute it, so that the next user reply matches the confirmation
                session.messages.pop() 
                
                yield json.dumps({"type": "confirmation", "message": confirm_prompt, "pending": True}) + "\n"
                yield json.dumps({"type": "done"}) + "\n"
                return
                
            # Otherwise, execute immediately
            result = execute_tool(db, name, arguments)
            
            # Yield trace of result
            success_emoji = "✅" if result.get("success") else "❌"
            yield json.dumps({"type": "trace", "message": f"{success_emoji} Tool `{name}` result: `{result.get('message')}`"}) + "\n"
            
            # Append tool result to messages
            session.messages.append({
                "role": "tool",
                "tool_call_id": tc_id,
                "name": name,
                "content": json.dumps(result)
            })
            
        # Continue loop so LLM can read tool outputs and call next tools or respond
        # (This is multi-step tool calling)
        
    # If we exceeded max iterations, warn and stop
    yield json.dumps({"type": "trace", "message": "⚠️ Cap of 6 agent iterations reached. Ending agent loop."}) + "\n"
    limit_msg = "I've hit my maximum thinking iterations. Let me know what you'd like to do next."
    session.messages.append({"role": "assistant", "content": limit_msg})
    yield json.dumps({"type": "content", "delta": limit_msg}) + "\n"
    yield json.dumps({"type": "done"}) + "\n"
