import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from models import Base, Profile, Hobby, Event, Setting

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///app.db")

# Create database engine
# SQLite needs connect_args={"check_same_thread": False} for multi-threaded access
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Dependency context manager for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def seed_db(db: Session):
    """Seed the database with mock user data."""
    # Ensure tables are created
    Base.metadata.create_all(bind=engine)

    # Check if data already exists (using profile id=1 as an indicator)
    profile_exists = db.query(Profile).filter(Profile.id == 1).first()
    if profile_exists:
        return

    # Seed User Profile
    profile = Profile(
        id=1,
        name="Alice Smith",
        dob="1995-06-15",
        email="alice@example.com",
        phone="+1-555-0199",
        bio="Passionate software engineer and outdoor enthusiast."
    )
    db.add(profile)

    # Seed Hobbies
    hobbies = [
        Hobby(name="Swimming", skill_level="intermediate"),
        Hobby(name="Reading", skill_level="advanced"),
        Hobby(name="Cooking", skill_level="beginner")
    ]
    db.add_all(hobbies)

    # Seed Events
    events = [
        Event(title="Tech Conference 2026", date="2026-06-10", location="San Francisco, CA"),
        Event(title="Weekly Team Sync", date="2026-06-03", location="Zoom Meeting")
    ]
    db.add_all(events)

    # Seed Settings
    settings = [
        Setting(key="theme", value="light"),
        Setting(key="language", value="English"),
        Setting(key="notifications", value="on"),
        Setting(key="timezone", value="America/New_York")
    ]
    db.add_all(settings)

    db.commit()

def reset_db():
    """Wipe database and re-seed with fresh mock data."""
    Base.metadata.drop_all(bind=engine)
    db = SessionLocal()
    try:
        seed_db(db)
    finally:
        db.close()
