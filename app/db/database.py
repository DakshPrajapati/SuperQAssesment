"""
Database configuration and session management.
Sets up SQLAlchemy engine, session, and dependency injection.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
from app.db.models import Base

# Create SQLAlchemy engine
engine = create_engine(
    settings.database_url,
    echo=False,  # Set to True for SQL debugging
    pool_pre_ping=True,  # Verify connections before using them
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """
    FastAPI dependency to get database session.
    Yields a database session and ensures it's closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize the database by creating all tables and pgvector extension.
    Call this during application startup.
    """
    # Create pgvector extension
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
