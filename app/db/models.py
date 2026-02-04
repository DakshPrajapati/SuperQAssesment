"""
SQLAlchemy ORM models for the chat service.
Defines Thread, Message, Summary, and ModelMetadata models with relationships.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

Base = declarative_base()


class Thread(Base):
    """
    Represents a chat thread with a persistent system prompt.
    
    Attributes:
        id: Unique identifier
        title: Thread title/name
        system_prompt: Static system prompt for this thread
        created_at: Timestamp when the thread was created
        messages: Relationship to Message objects
        summaries: Relationship to Summary objects
    """
    __tablename__ = "threads"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    system_prompt = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    messages = relationship("Message", back_populates="thread", cascade="all, delete-orphan")
    summaries = relationship("Summary", back_populates="thread", cascade="all, delete-orphan")


class Message(Base):
    """
    Represents a single message in a chat thread.
    
    Attributes:
        id: Unique identifier
        thread_id: Foreign key to Thread
        sender: Name or identifier of the message sender
        role: Either 'user' or 'agent' to indicate message origin
        content: The actual message content
        model_used: The LLM model used to generate this message (if agent)
        timestamp: When the message was created
        thread: Relationship back to Thread
    """
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Integer, ForeignKey("threads.id"), nullable=False, index=True)
    sender = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)  # 'user' or 'agent'
    content = Column(Text, nullable=False)
    model_used = Column(String(255), nullable=True)  # LLM model name if agent
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    thread = relationship("Thread", back_populates="messages")
    
    # Index for efficient querying
    __table_args__ = (
        Index('ix_messages_thread_timestamp', 'thread_id', 'timestamp'),
    )


class Summary(Base):
    """
    Represents a structured conversation summary with multiple components.
    
    Attributes:
        id: Unique identifier
        thread_id: Foreign key to Thread
        summary_data: JSON object containing structured summary with:
            - core_facts: List of fundamental facts discussed
            - user_preferences: List of user preferences mentioned
            - decisions_made: List of decisions that were made
            - constraints: List of constraints or limitations
            - open_questions: List of unresolved questions
            - entities: Dictionary of entities (people, companies, etc.)
        embedding: Vector embedding of the summary for semantic search
        created_at: When the summary was generated
        message_count: Number of messages summarized
        thread: Relationship back to Thread
    """
    __tablename__ = "summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Integer, ForeignKey("threads.id"), nullable=False, index=True)
    summary_data = Column(JSON, nullable=False, default={
        "core_facts": [],
        "user_preferences": [],
        "decisions_made": [],
        "constraints": [],
        "open_questions": [],
        "entities": {}
    })
    embedding = Column(Vector(1536), nullable=True)  # OpenAI embedding dimension
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    message_count = Column(Integer, default=0)  # Number of messages included
    
    # Relationships
    thread = relationship("Thread", back_populates="summaries")

class ModelMetadata(Base):
    """
    Metadata for LLM models including summary size preference.
    
    Attributes:
        id: Unique identifier
        model_name: The model identifier (e.g., "google/gemini-pro")
        summary_type: Size of summary to use ('small', 'medium', 'large')
            - small: core_facts only
            - medium: core_facts + decisions_made + open_questions
            - large: all fields
        max_tokens: Maximum tokens the model can handle
        description: Human-readable description of the model
        created_at: When the metadata was created
        updated_at: Last update timestamp
    """
    __tablename__ = "model_metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(255), unique=True, nullable=False, index=True)
    summary_type = Column(String(50), default="medium", nullable=False)  # small, medium, large
    max_tokens = Column(Integer, default=4096)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)