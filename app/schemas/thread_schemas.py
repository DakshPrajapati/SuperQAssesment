"""
Pydantic schemas for thread request/response validation.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from app.schemas.message_schemas import MessageResponse


class ThreadCreate(BaseModel):
    """Schema for creating a new thread."""
    title: str = Field(..., description="Thread title")
    system_prompt: str = Field(..., description="System prompt for the thread")


class SummaryData(BaseModel):
    """Schema for structured summary data."""
    core_facts: List[str] = Field(default_factory=list, description="Fundamental facts discussed")
    user_preferences: List[str] = Field(default_factory=list, description="User preferences mentioned")
    decisions_made: List[str] = Field(default_factory=list, description="Decisions that were made")
    constraints: List[str] = Field(default_factory=list, description="Constraints or limitations")
    open_questions: List[str] = Field(default_factory=list, description="Unresolved questions")
    # Entities can be simple strings or nested structures (dicts/lists).
    entities: Dict[str, Any] = Field(default_factory=dict, description="Important entities and their roles or nested data")
    unlabeled: List[str] = Field(default_factory=list, description="Important content that doesn't fit the above categories")
    
    model_config = {"protected_namespaces": ()}


class SummaryResponse(BaseModel):
    """Schema for summary response."""
    id: int
    thread_id: int
    summary_data: SummaryData
    created_at: datetime
    message_count: int
    
    model_config = {"protected_namespaces": ()}


class ThreadResponse(BaseModel):
    """Schema for basic thread response."""
    id: int
    title: str
    system_prompt: str
    created_at: datetime
    
    model_config = {"protected_namespaces": ()}


class ThreadUpdate(BaseModel):
    """Schema for updating a thread's mutable fields."""
    system_prompt: str

    model_config = {"protected_namespaces": ()}


class Thread(BaseModel):
    """Comprehensive thread schema with messages and summaries."""
    id: int
    title: str
    system_prompt: str
    created_at: datetime
    messages: List[MessageResponse] = []
    summaries: List[SummaryResponse] = []
    
    model_config = {"protected_namespaces": ()}


class ModelMetadataResponse(BaseModel):
    """Schema for model metadata."""
    id: int
    model_name: str
    summary_type: str = Field(..., description="Size of summary: 'small', 'medium', or 'large'")
    max_tokens: int
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"protected_namespaces": ()}


class ModelMetadataCreate(BaseModel):
    """Schema for creating/updating model metadata."""
    model_name: str = Field(..., description="The model identifier")
    summary_type: str = Field(default="medium", description="Summary size: small/medium/large")
    max_tokens: int = Field(default=4096, description="Maximum tokens")
    description: Optional[str] = Field(None, description="Model description")
