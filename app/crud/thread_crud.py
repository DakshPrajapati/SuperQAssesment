"""
CRUD operations for database interactions.
Functions for creating, reading, and updating threads, messages, and summaries.
"""

from datetime import datetime
from sqlalchemy.orm import Session
from app.db.models import Thread, Message, Summary, ModelMetadata
from app.schemas.thread_schemas import ThreadCreate
from typing import List, Optional, Dict, Any


def create_thread(db: Session, thread: ThreadCreate) -> Thread:
    """
    Create a new thread in the database.
    
    Args:
        db: Database session
        thread: ThreadCreate schema with title and system_prompt
        
    Returns:
        The created Thread object
    """
    db_thread = Thread(
        title=thread.title,
        system_prompt=thread.system_prompt
    )
    db.add(db_thread)
    db.commit()
    db.refresh(db_thread)
    return db_thread


def get_thread(db: Session, thread_id: int) -> Optional[Thread]:
    """
    Retrieve a thread by ID.
    
    Args:
        db: Database session
        thread_id: ID of the thread
        
    Returns:
        The Thread object or None if not found
    """
    return db.query(Thread).filter(Thread.id == thread_id).first()


def get_threads(db: Session, skip: int = 0, limit: int = 100) -> List[Thread]:
    """
    Retrieve a list of all threads with pagination.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of Thread objects
    """
    return db.query(Thread).offset(skip).limit(limit).all()


def add_message_to_thread(
    db: Session,
    thread_id: int,
    sender: str,
    role: str,
    content: str,
    model_used: Optional[str] = None
) -> Message:
    """
    Add a new message to a specific thread.
    
    Args:
        db: Database session
        thread_id: ID of the thread
        sender: Name/ID of the sender
        role: Either 'user' or 'agent'
        content: The message content (must be string)
        model_used: LLM model used (if agent-generated)
        
    Returns:
        The created Message object
        
    Raises:
        ValueError: If content is not a string (error code: INVALID_MESSAGE_CONTENT)
    """
    # Validate that content is a string
    if not isinstance(content, str):
        error_msg = (
            f"ERROR_INVALID_MESSAGE_CONTENT: Message content must be a string, "
            f"got {type(content).__name__}. This usually means the API response was not "
            f"properly unpacked. Ensure you're extracting the text from tuple responses."
        )
        raise ValueError(error_msg)
    
    message = Message(
        thread_id=thread_id,
        sender=sender,
        role=role,
        content=content,
        model_used=model_used,
        timestamp=datetime.utcnow()
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def add_summary_to_thread(
    db: Session,
    thread_id: int,
    summary_data: Dict[str, Any],
    message_count: int,
    embedding: Optional[List[float]] = None
) -> Summary:
    """
    Add a new structured summary to a specific thread.
    
    Args:
        db: Database session
        thread_id: ID of the thread
        summary_data: Dictionary with structured summary containing:
            - core_facts: List of facts
            - user_preferences: List of preferences
            - decisions_made: List of decisions
            - constraints: List of constraints
            - open_questions: List of open questions
            - entities: Dict of entities
        message_count: Number of messages summarized
        embedding: Optional vector embedding
        
    Returns:
        The created Summary object
    """
    # If a summary already exists for this thread, replace/update it
    existing = db.query(Summary).filter(Summary.thread_id == thread_id).order_by(Summary.created_at.desc()).first()
    if existing:
        existing.summary_data = summary_data
        existing.message_count = message_count
        if embedding is not None:
            existing.embedding = embedding
        existing.created_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    # Otherwise create a new summary
    summary = Summary(
        thread_id=thread_id,
        summary_data=summary_data,
        message_count=message_count,
        embedding=embedding,
        created_at=datetime.utcnow()
    )
    db.add(summary)
    db.commit()
    db.refresh(summary)
    return summary


def get_messages_for_thread(
    db: Session,
    thread_id: int,
    exclude_before_summary: bool = True
) -> List[Message]:
    """
    Retrieve all messages for a thread.
    If exclude_before_summary is True, excludes messages before the last summary.
    
    Args:
        db: Database session
        thread_id: ID of the thread
        exclude_before_summary: Whether to exclude old messages
        
    Returns:
        List of Message objects
    """
    query = db.query(Message).filter(Message.thread_id == thread_id)

    if exclude_before_summary:
        # Prefer an explicit Summary row's timestamp; if none exists,
        # fall back to a timestamp stored on the Thread record.
        from datetime import datetime as _dt

        last_summary_ts = get_last_summary_timestamp_for_thread(db, thread_id)

        if last_summary_ts and isinstance(last_summary_ts, _dt):
            query = query.filter(Message.timestamp > last_summary_ts)

    return query.order_by(Message.timestamp).all()


def get_last_summary_timestamp_for_thread(db: Session, thread_id: int) -> Optional[datetime]:
    """
    Return the most recent summary timestamp for a thread.

    Lookup order:
    1. `Summary.created_at` (most recent Summary row)
    2. Fallback: common timestamp-like fields on the `Thread` record

    This helper is useful when the `summaries` table has not been populated
    and a last-summary timestamp was stored directly on the `threads` table.
    """

    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        return None

    # Return the most recent Summary.created_at if summaries exist.
    # Avoid indexing into an empty list which caused IndexError when no summaries are present.
    if thread.summaries and len(thread.summaries) > 0:
        return thread.summaries[0].created_at

    # No summaries available — return None so callers can fall back appropriately.
    return None

def get_last_summary_for_thread(db: Session, thread_id: int) -> Optional[Summary]:
    """
    Retrieve the most recent summary for a thread.
    
    Args:
        db: Database session
        thread_id: ID of the thread
        
    Returns:
        The most recent Summary object or None if no summaries exist
    """
    return db.query(Summary).filter(
        Summary.thread_id == thread_id
    ).order_by(Summary.created_at.desc()).first()


def get_summaries_for_thread(db: Session, thread_id: int) -> List[Summary]:
    """
    Retrieve all summaries for a thread.
    
    Args:
        db: Database session
        thread_id: ID of the thread
        
    Returns:
        List of Summary objects ordered by creation time
    """
    return db.query(Summary).filter(
        Summary.thread_id == thread_id
    ).order_by(Summary.created_at).all()


def update_thread_system_prompt(db: Session, thread_id: int, system_prompt: str) -> Optional[Thread]:
    """
    Update the system prompt for a thread.

    Args:
        db: Database session
        thread_id: ID of the thread
        system_prompt: New system prompt text

    Returns:
        The updated Thread object or None if not found
    """
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        return None
    thread.system_prompt = system_prompt
    db.commit()
    db.refresh(thread)
    return thread


def delete_thread(db: Session, thread_id: int) -> bool:
    """
    Delete a thread and its related messages/summaries.

    Args:
        db: Database session
        thread_id: ID of the thread

    Returns:
        True if deleted, False if not found
    """
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        return False
    db.delete(thread)
    db.commit()
    return True

# ===================== ModelMetadata CRUD Operations =====================

def create_or_update_model_metadata(
    db: Session,
    model_name: str,
    summary_type: str = "medium",
    max_tokens: int = 4096,
    description: Optional[str] = None
) -> ModelMetadata:
    """
    Create or update model metadata.
    
    Args:
        db: Database session
        model_name: The model identifier (e.g., "google/gemini-pro")
        summary_type: Size of summary to use ('small', 'medium', 'large')
        max_tokens: Maximum tokens for the model
        description: Human-readable description
        
    Returns:
        The created or updated ModelMetadata object
    """
    metadata = db.query(ModelMetadata).filter(
        ModelMetadata.model_name == model_name
    ).first()
    
    if metadata:
        # Update existing
        metadata.summary_type = summary_type
        metadata.max_tokens = max_tokens
        if description:
            metadata.description = description
        metadata.updated_at = datetime.utcnow()
    else:
        # Create new
        metadata = ModelMetadata(
            model_name=model_name,
            summary_type=summary_type,
            max_tokens=max_tokens,
            description=description
        )
        db.add(metadata)
    
    db.commit()
    db.refresh(metadata)
    return metadata


def get_model_metadata(db: Session, model_name: str) -> Optional[ModelMetadata]:
    """
    Get metadata for a specific model.
    
    Args:
        db: Database session
        model_name: The model identifier
        
    Returns:
        The ModelMetadata object or None if not found
    """
    return db.query(ModelMetadata).filter(
        ModelMetadata.model_name == model_name
    ).first()


def get_all_model_metadata(db: Session) -> List[ModelMetadata]:
    """
    Get all model metadata.
    
    Args:
        db: Database session
        
    Returns:
        List of all ModelMetadata objects
    """
    return db.query(ModelMetadata).all()


def delete_model_metadata(db: Session, model_name: str) -> bool:
    """
    Delete model metadata.
    
    Args:
        db: Database session
        model_name: The model identifier
        
    Returns:
        True if deleted, False if not found
    """
    metadata = db.query(ModelMetadata).filter(
        ModelMetadata.model_name == model_name
    ).first()
    
    if metadata:
        db.delete(metadata)
        db.commit()
        return True
    return False