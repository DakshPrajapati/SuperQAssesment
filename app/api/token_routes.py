"""
API routes for token counting and context window management.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from app.utils.token_counter import TokenCounter, ContextWindowManager
from app.core.models import get_available_models

router = APIRouter(prefix="/tokens", tags=["tokens"])


@router.post("/count")
async def count_tokens_endpoint(
    text: str = Query(..., min_length=1, description="Text to count tokens for"),
    model: str = Query(..., description="Model name (e.g., 'google/gemini-pro')")
) -> Dict[str, Any]:
    """
    Count approximate tokens for given text and model.
    
    Args:
        text: Text to count tokens for
        model: Model name
        
    Returns:
        Token count and related information
    """
    try:
        token_count = TokenCounter.count_tokens(text, model)
        return {
            "text": text,
            "model": model,
            "tokens": token_count,
            "text_length": len(text),
            "word_count": len(text.split())
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/count-messages")
async def count_messages_tokens_endpoint(
    messages: List[Dict[str, str]],
    model: str = Query(..., description="Model name"),
    system_prompt: Optional[str] = Query(None, description="Optional system prompt")
) -> Dict[str, Any]:
    """
    Count tokens for a list of messages.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Model name
        system_prompt: Optional system prompt
        
    Returns:
        Total token count for all messages
    """
    try:
        total_tokens = TokenCounter.count_messages_tokens(
            messages,
            model,
            system_prompt or ""
        )
        return {
            "model": model,
            "total_tokens": total_tokens,
            "message_count": len(messages),
            "has_system_prompt": bool(system_prompt),
            "system_prompt": system_prompt if system_prompt else None
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/validate/{model}")
async def validate_context_endpoint(
    model: str,
    used_tokens: int = Query(..., ge=0, description="Number of tokens used"),
    buffer: int = Query(100, ge=0, description="Safety buffer in tokens")
) -> Dict[str, Any]:
    """
    Validate if token usage is within acceptable limits.
    
    Args:
        model: Model name
        used_tokens: Number of tokens currently used
        buffer: Safety buffer to reserve
        
    Returns:
        Validation results including remaining tokens and usage percentage
    """
    try:
        return TokenCounter.validate_context(model, used_tokens, buffer)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status/{model}")
async def context_status_endpoint(
    model: str,
    used_tokens: int = Query(0, ge=0, description="Number of tokens used")
) -> Dict[str, Any]:
    """
    Get detailed context window status for a model.
    
    Args:
        model: Model name
        used_tokens: Number of tokens used
        
    Returns:
        Detailed status information
    """
    try:
        manager = ContextWindowManager(model)
        manager.used_tokens = used_tokens
        return manager.get_status()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/available-tokens/{model}")
async def available_tokens_endpoint(
    model: str,
    used_tokens: int = Query(0, ge=0, description="Number of tokens used"),
    buffer: int = Query(500, ge=0, description="Safety buffer in tokens")
) -> Dict[str, Any]:
    """
    Get available tokens remaining for a model (accounting for safety buffer).
    
    Args:
        model: Model name
        used_tokens: Number of tokens used
        buffer: Safety buffer to reserve
        
    Returns:
        Available tokens information
    """
    try:
        manager = ContextWindowManager(model, buffer)
        manager.used_tokens = used_tokens
        
        return {
            "model": model,
            "available_tokens": manager.get_available_tokens(),
            "buffer": buffer,
            "used_tokens": used_tokens,
            "context_window": manager.config.context_window,
            "is_safe": manager.is_safe(),
            "percentage_used": round((used_tokens / manager.config.context_window) * 100, 2)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/check-fit")
async def check_fit_endpoint(
    text: str = Query(..., min_length=1, description="Text to check"),
    model: str = Query(..., description="Model name"),
    used_tokens: int = Query(0, ge=0, description="Tokens already used"),
    buffer: int = Query(500, ge=0, description="Safety buffer in tokens")
) -> Dict[str, Any]:
    """
    Check if new text can fit within context window.
    
    Args:
        text: Text to check
        model: Model name
        used_tokens: Tokens already used
        buffer: Safety buffer in tokens
        
    Returns:
        Whether text can fit and related information
    """
    try:
        manager = ContextWindowManager(model, buffer)
        manager.used_tokens = used_tokens
        
        can_fit = manager.can_fit(text)
        tokens_needed = TokenCounter.count_tokens(text, model)
        available = manager.get_available_tokens()
        
        return {
            "can_fit": can_fit,
            "text_tokens": tokens_needed,
            "available_tokens": available,
            "used_tokens": used_tokens,
            "buffer": buffer,
            "shortage": max(0, tokens_needed - available),
            "model": model
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/models-info")
async def models_info_endpoint() -> Dict[str, Any]:
    """
    Get token and context information for all available models.
    
    Returns:
        Information about context windows and max tokens for all models
    """
    models = get_available_models()
    
    enhanced = {}
    for model_name, config in models.items():
        enhanced[model_name] = {
            **config,
            "context_window": config.get("context_window", "Unknown"),
            "max_output_tokens": config.get("max_tokens", "Unknown"),
        }
    
    return {
        "total_models": len(enhanced),
        "models": enhanced
    }
