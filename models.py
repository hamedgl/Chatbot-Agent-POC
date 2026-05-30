from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Text

class Base(DeclarativeBase):
    """Base class for SQLAlchemy ORM models."""
    pass

class Profile(Base):
    """Model to store the mock user profile."""
    __tablename__ = "profiles"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    dob: Mapped[str] = mapped_column(String(20), nullable=False)  # Expected format: YYYY-MM-DD
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    bio: Mapped[str] = mapped_column(Text, nullable=False)

class Hobby(Base):
    """Model to store user hobbies."""
    __tablename__ = "hobbies"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    skill_level: Mapped[str] = mapped_column(String(50), nullable=False)  # beginner | intermediate | advanced

class Event(Base):
    """Model to store personal schedule events."""
    __tablename__ = "events"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    date: Mapped[str] = mapped_column(String(20), nullable=False)  # Expected format: YYYY-MM-DD
    location: Mapped[str] = mapped_column(String(150), nullable=False)

class Setting(Base):
    """Model to store user preferences and settings."""
    __tablename__ = "settings"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)  # theme | language | notifications | timezone
    value: Mapped[str] = mapped_column(String(100), nullable=False)
