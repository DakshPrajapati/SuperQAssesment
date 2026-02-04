"""
FastAPI routes for the chat service.
Defines all API endpoints for thread and message management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.crud import thread_crud
from app.services.thread_service import ThreadService
from app.schemas.thread_schemas import (
    ThreadCreate,
    ThreadResponse,
    Thread as ThreadSchema,
    SummaryResponse,
    ThreadUpdate,
    ModelMetadataResponse,
    ModelMetadataCreate
)
from app.schemas.message_schemas import MessageCreate, MessageResponse
from app.core.models import get_model_config, get_available_models
from typing import List, Dict, Any

router = APIRouter(prefix="/threads", tags=["threads"])
thread_service = ThreadService()

@router.get(
    "/available-models",
    response_model=Dict[str, Any],
    summary="List all available models from registry",
    tags=["models"],
    responses={
        200: {"description": "All available models with their configurations"}
    }
)
async def list_available_models():
    """
    Get all available LLM models from the model registry.
    
    This endpoint returns all registered models with their configurations,
    including capabilities like vision support, function calling, token limits, etc.
    
    Use these model names when sending messages or creating agents.
    
    **Returns:**
    - 200: Dictionary of all available models with their configurations
    
    **Example Response:**
    ```json
    {
        "openai/gpt-4": {
            "provider": "openai",
            "max_tokens": 8192,
            "temperature": 0.7,
            "supports_vision": false,
            "supports_function_calling": true,
            "context_window": 8192,
            "preferred_summary_size": "large",
            "description": "OpenAI's most capable model with excellent reasoning"
        },
        "upstage/solar-pro-3:free": { ... }
    }
    ```
    """
    return get_available_models()

@router.post(
    "/",
    response_model=ThreadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new chat thread",
    responses={
        201: {"description": "Thread created successfully"},
        422: {"description": "Invalid request data"}
    }
)
async def create_thread(
    thread: ThreadCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new chat thread with a system prompt.
    
    **Parameters:**
    - **title**: Display name for the thread
    - **system_prompt**: System prompt that guides the LLM behavior throughout the thread
    
    **Example:**
    ```json
    {
        "title": "Customer Support Chat",
        "system_prompt": "You are a helpful customer support assistant. Always be polite and professional."
    }
    ```
    
    **Returns:**
    - 201: Created thread object with ID, title, system_prompt, and creation timestamp
    """
    db_thread = thread_crud.create_thread(db, thread)
    return db_thread


@router.get(
    "/",
    response_model=List[ThreadResponse],
    summary="List all chat threads",
    responses={
        200: {"description": "List of threads"}
    }
)
async def list_threads(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Retrieve all existing chat threads.
    
    **Parameters:**
    - **skip**: Number of threads to skip (for pagination)
    - **limit**: Maximum number of threads to return
    
    **Returns:**
    - 200: List of thread objects
    """
    threads = thread_crud.get_threads(db, skip=skip, limit=limit)
    return threads


@router.get(
    "/{thread_id}",
    response_model=ThreadSchema,
    summary="Get thread details",
    responses={
        200: {"description": "Thread details with messages and summaries"},
        404: {"description": "Thread not found"}
    }
)
async def get_thread_details(
    thread_id: int,
    db: Session = Depends(get_db)
):
    """
    Retrieve detailed information about a specific thread.
    
    Includes all messages and summaries for the thread.
    
    **Parameters:**
    - **thread_id**: ID of the thread
    
    **Returns:**
    - 200: Complete thread object with nested messages and summaries
    - 404: Thread not found
    """
    thread = thread_crud.get_thread(db, thread_id)
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Thread {thread_id} not found"
        )
    return thread


@router.patch(
    "/{thread_id}",
    response_model=ThreadResponse,
    summary="Update a thread's system prompt",
    responses={
        200: {"description": "Thread updated"},
        404: {"description": "Thread not found"}
    }
)
async def update_thread(
    thread_id: int,
    payload: ThreadUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a thread's mutable fields (currently only `system_prompt`).
    """
    thread = thread_crud.get_thread(db, thread_id)
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Thread {thread_id} not found"
        )

    updated = thread_crud.update_thread_system_prompt(db, thread_id, payload.system_prompt)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Thread {thread_id} not found"
        )
    return updated


@router.delete(
    "/{thread_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a thread",
    responses={
        204: {"description": "Thread deleted"},
        404: {"description": "Thread not found"}
    }
)
async def delete_thread(
    thread_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a thread and all related messages/summaries.
    """
    thread = thread_crud.get_thread(db, thread_id)
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Thread {thread_id} not found"
        )
    deleted = thread_crud.delete_thread(db, thread_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Thread {thread_id} not found"
        )
    return None


@router.post(
    "/{thread_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a message and get LLM response",
    responses={
        201: {"description": "Agent response generated"},
        404: {"description": "Thread not found"},
        422: {"description": "Invalid request data"}
    }
)
async def send_message(
    thread_id: int,
    message: MessageCreate,
    db: Session = Depends(get_db)
):
    """
    Send a user message to a thread and receive an agent response.
    
    This endpoint:
    1. Saves the user's message
    2. Generates an LLM response using the specified model
    3. Saves the agent's response
    4. May trigger automatic conversation summarization
    
    **Parameters:**
    - **thread_id**: ID of the thread to send message to
    - **sender**: Name/ID of the user
    - **content**: The message text
    - **model**: LLM model to use (must be a valid registered model)
    
    **Example:**
    ```json
    {
        "sender": "user123",
        "content": "What is the weather like?",
        "model": "openai/gpt-4-turbo-preview"
    }
    ```
    
    **Returns:**
    - 201: The agent's response message
    - 404: Thread not found
    - 400: Invalid or non-existent model
    """
    model = message.model or "upstage/solar-pro-3:free"
    
    # Check if thread exists
    thread = thread_crud.get_thread(db, thread_id)
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Thread {thread_id} not found"
        )
    
    # Use default model if not specifie
    
    # Validate that the model exists in the registry
    try:
        get_model_config(model)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid model: {str(e)}. Use /models/ endpoint to see available models."
        )
    
    try:
        response = await thread_service.process_user_message(
            db=db,
            thread_id=thread_id,
            sender=message.sender,
            user_message=message.content,
            model=model
        )
        return response
    except ValueError as e:
        # Handle validation errors (e.g., invalid message content type)
        error_detail = str(e)
        if "ERROR_INVALID_MESSAGE_CONTENT" in error_detail:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=error_detail
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_detail
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing message: {str(e)}"
        )


@router.get(
    "/{thread_id}/summaries",
    response_model=List[SummaryResponse],
    summary="Get thread summaries",
    responses={
        200: {"description": "List of summaries"},
        404: {"description": "Thread not found"}
    }
)
async def get_thread_summaries(
    thread_id: int,
    db: Session = Depends(get_db)
):
    """
    Retrieve all conversation summaries for a specific thread.
    
    Summaries are generated automatically as conversations grow,
    helping maintain context while reducing token usage.
    
    **Parameters:**
    - **thread_id**: ID of the thread
    
    **Returns:**
    - 200: List of summary objects ordered by creation time
    - 404: Thread not found
    """
    thread = thread_crud.get_thread(db, thread_id)
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Thread {thread_id} not found"
        )
    
    summaries = thread_crud.get_summaries_for_thread(db, thread_id)
    return summaries

# ===================== Model Metadata Routes =====================

