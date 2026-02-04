"""
Pydantic schemas for message request/response validation.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    """Schema for creating a new message."""
    sender: str = Field(..., description="Name or ID of the message sender")
    content: str = Field(..., description="The message content")
    model: Optional[str] = Field(None, description="LLM model to use for agent response")


class MessageResponse(BaseModel):
    """Schema for message response."""
    id: int
    thread_id: int
    sender: str
    role: str  # 'user' or 'agent'
    content: str
    model_used: Optional[str] = None
    timestamp: datetime
    
    class Config:
        from_attributes = True


class Message(BaseModel):
    """Comprehensive message schema."""
    id: int
    thread_id: int
    sender: str
    role: str
    content: str
    model_used: Optional[str] = None
    timestamp: datetime
    
    class Config:
        from_attributes = True
