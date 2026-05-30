import re
from datetime import datetime
from sqlalchemy.orm import Session
from models import Profile, Hobby, Event, Setting

# Input validation helpers
def validate_date(date_str: str) -> bool:
    """Validate that date matches YYYY-MM-DD format."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def validate_email(email_str: str) -> bool:
    """Validate standard email formats."""
    email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return bool(re.match(email_regex, email_str))

# --- PROFILE TOOLS ---

def get_profile(db: Session) -> dict:
    """
    Get the mock user's profile information (name, dob, email, phone, bio).
    
    Args:
        db: Database session.
        
    Returns:
        A dictionary containing success status, a message, and profile data.
    """
    profile = db.query(Profile).filter(Profile.id == 1).first()
    if not profile:
        return {"success": False, "message": "Profile not found."}
    
    return {
        "success": True,
        "message": "Successfully retrieved profile.",
        "data": {
            "name": profile.name,
            "dob": profile.dob,
            "email": profile.email,
            "phone": profile.phone,
            "bio": profile.bio
        }
    }

def update_profile(db: Session, field: str, value: str) -> dict:
    """
    Update a specific field of the user's profile.
    
    Args:
        db: Database session.
        field: The field to update. Must be one of: 'name', 'dob', 'email', 'phone', 'bio'.
        value: The new value for the field. If value is empty or '', it represents a wipe/clear.
        
    Returns:
        A dictionary containing success status and a description of the change.
    """
    field = field.lower().strip()
    valid_fields = ["name", "dob", "email", "phone", "bio"]
    
    if field not in valid_fields:
        return {
            "success": False,
            "message": f"Invalid field '{field}'. Allowed fields are: {', '.join(valid_fields)}."
        }
    
    profile = db.query(Profile).filter(Profile.id == 1).first()
    if not profile:
        return {"success": False, "message": "Profile not found."}
    
    # Input validation for specific fields (unless doing a wipe)
    value_stripped = value.strip()
    if value_stripped not in ["", "None", "null"]:
        if field == "dob" and not validate_date(value_stripped):
            return {"success": False, "message": "Invalid date format. Please use YYYY-MM-DD."}
        if field == "email" and not validate_email(value_stripped):
            return {"success": False, "message": "Invalid email address format."}
        if field == "phone" and len(value_stripped) < 5:
            return {"success": False, "message": "Phone number is too short."}
    else:
        # Convert clear terms to empty string
        value_stripped = ""

    # Perform the update
    old_value = getattr(profile, field)
    setattr(profile, field, value_stripped)
    db.commit()
    
    action_type = "cleared" if value_stripped == "" else f"updated to '{value_stripped}'"
    return {
        "success": True,
        "message": f"Profile field '{field}' was successfully {action_type}.",
        "data": {
            "field": field,
            "old_value": old_value,
            "new_value": value_stripped
        }
    }

# --- HOBBIES TOOLS ---

def list_hobbies(db: Session) -> dict:
    """
    List all the user's hobbies and skill levels.
    
    Args:
        db: Database session.
        
    Returns:
        A dictionary containing success status, message, and list of hobbies.
    """
    hobbies = db.query(Hobby).all()
    hobbies_list = [{"name": h.name, "skill_level": h.skill_level} for h in hobbies]
    return {
        "success": True,
        "message": f"Successfully retrieved {len(hobbies_list)} hobbies.",
        "data": hobbies_list
    }

def add_hobby(db: Session, name: str, skill_level: str) -> dict:
    """
    Add a new hobby for the user with a specified skill level.
    
    Args:
        db: Database session.
        name: Name of the hobby.
        skill_level: Skill level. Must be 'beginner', 'intermediate', or 'advanced'.
        
    Returns:
        A dictionary containing success status and confirmation message.
    """
    name = name.strip()
    skill_level = skill_level.lower().strip()
    
    valid_levels = ["beginner", "intermediate", "advanced"]
    if skill_level not in valid_levels:
        return {
            "success": False,
            "message": f"Invalid skill level '{skill_level}'. Must be one of: {', '.join(valid_levels)}."
        }
    
    if not name:
        return {"success": False, "message": "Hobby name cannot be empty."}
    
    # Check if hobby already exists
    existing = db.query(Hobby).filter(Hobby.name.ilike(name)).first()
    if existing:
        old_level = existing.skill_level
        existing.skill_level = skill_level
        db.commit()
        return {
            "success": True,
            "message": f"Hobby '{name}' already existed. Updated skill level from '{old_level}' to '{skill_level}'.",
            "data": {"name": name, "skill_level": skill_level}
        }
    
    # Add new
    new_hobby = Hobby(name=name, skill_level=skill_level)
    db.add(new_hobby)
    db.commit()
    
    return {
        "success": True,
        "message": f"Successfully added hobby '{name}' with skill level '{skill_level}'.",
        "data": {"name": name, "skill_level": skill_level}
    }

def remove_hobby(db: Session, name: str) -> dict:
    """
    Remove a hobby from the user's list. (DESTRUCTIVE ACTION)
    
    Args:
        db: Database session.
        name: Name of the hobby to remove.
        
    Returns:
        A dictionary containing success status and confirmation message.
    """
    name = name.strip()
    hobby = db.query(Hobby).filter(Hobby.name.ilike(name)).first()
    
    if not hobby:
        return {"success": False, "message": f"Hobby '{name}' not found."}
    
    db.delete(hobby)
    db.commit()
    
    return {
        "success": True,
        "message": f"Successfully removed hobby '{name}'.",
        "data": {"name": name}
    }

# --- EVENTS TOOLS ---

def list_events(db: Session) -> dict:
    """
    List all scheduled events.
    
    Args:
        db: Database session.
        
    Returns:
        A dictionary containing success status, message, and list of events.
    """
    events = db.query(Event).order_by(Event.date).all()
    events_list = [{"id": e.id, "title": e.title, "date": e.date, "location": e.location} for e in events]
    return {
        "success": True,
        "message": f"Successfully retrieved {len(events_list)} scheduled events.",
        "data": events_list
    }

def create_event(db: Session, title: str, date: str, location: str) -> dict:
    """
    Create a new scheduled event.
    
    Args:
        db: Database session.
        title: Title of the event.
        date: Date of the event. Must be in YYYY-MM-DD format.
        location: Location of the event.
        
    Returns:
        A dictionary containing success status and details of the created event.
    """
    title = title.strip()
    date = date.strip()
    location = location.strip()
    
    if not title:
        return {"success": False, "message": "Event title cannot be empty."}
    if not date or not validate_date(date):
        return {"success": False, "message": "Invalid date. Please use YYYY-MM-DD format."}
    if not location:
        return {"success": False, "message": "Event location cannot be empty."}
        
    new_event = Event(title=title, date=date, location=location)
    db.add(new_event)
    db.commit()
    
    return {
        "success": True,
        "message": f"Successfully scheduled event '{title}' on {date} at {location}.",
        "data": {
            "id": new_event.id,
            "title": title,
            "date": date,
            "location": location
        }
    }

def cancel_event(db: Session, event_id: int) -> dict:
    """
    Cancel and delete an event by its ID. (DESTRUCTIVE ACTION)
    
    Args:
        db: Database session.
        event_id: The numeric ID of the event to cancel.
        
    Returns:
        A dictionary containing success status and confirmation message.
    """
    try:
        event_id = int(event_id)
    except (ValueError, TypeError):
        return {"success": False, "message": "Event ID must be a numeric integer."}
        
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        return {"success": False, "message": f"Event with ID {event_id} not found."}
        
    title = event.title
    db.delete(event)
    db.commit()
    
    return {
        "success": True,
        "message": f"Successfully cancelled event '{title}' (ID {event_id}).",
        "data": {"id": event_id, "title": title}
    }

# --- SETTINGS TOOLS ---

def get_settings(db: Session) -> dict:
    """
    Get all user settings and preferences.
    
    Args:
        db: Database session.
        
    Returns:
        A dictionary containing success status, message, and settings keys and values.
    """
    settings = db.query(Setting).all()
    settings_dict = {s.key: s.value for s in settings}
    return {
        "success": True,
        "message": "Successfully retrieved settings.",
        "data": settings_dict
    }

def update_setting(db: Session, key: str, value: str) -> dict:
    """
    Update the value of a specific setting key.
    
    Args:
        db: Database session.
        key: The setting key to update. Must be one of: 'theme', 'language', 'notifications', 'timezone'.
        value: The value to set. 'theme' must be 'light' or 'dark'. 'notifications' must be 'on' or 'off'.
        
    Returns:
        A dictionary containing success status and change description.
    """
    key = key.lower().strip()
    value = value.strip()
    
    allowed_keys = ["theme", "language", "notifications", "timezone"]
    if key not in allowed_keys:
        return {
            "success": False,
            "message": f"Invalid setting key '{key}'. Allowed keys: {', '.join(allowed_keys)}."
        }
        
    # Validations for values
    if key == "theme" and value.lower() not in ["light", "dark"]:
        return {"success": False, "message": "Theme must be 'light' or 'dark'."}
    if key == "notifications" and value.lower() not in ["on", "off"]:
        return {"success": False, "message": "Notifications must be 'on' or 'off'."}
        
    setting = db.query(Setting).filter(Setting.key == key).first()
    old_value = None
    
    if setting:
        old_value = setting.value
        setting.value = value
    else:
        setting = Setting(key=key, value=value)
        db.add(setting)
        
    db.commit()
    
    return {
        "success": True,
        "message": f"Setting '{key}' successfully updated to '{value}'.",
        "data": {
            "key": key,
            "old_value": old_value,
            "new_value": value
        }
    }
