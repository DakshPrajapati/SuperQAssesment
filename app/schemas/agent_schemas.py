"""
Pydantic schemas for agent-related API operations.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.agents.agent_definitions import AgentRole


class AgentRequest(BaseModel):
    """Schema for single agent request."""
    content: str = Field(..., description="User input for the agent to process")
    agent_role: AgentRole = Field(..., description="Which agent to use")
    context: Optional[Dict[str, Any]] = Field(None, description="Optional context")


class AgentTeamRequest(BaseModel):
    """Schema for multi-agent team request."""
    content: str = Field(..., description="User input")
    agent_roles: List[AgentRole] = Field(
        ...,
        description="List of agent roles to use"
    )
    context: Optional[Dict[str, Any]] = Field(None, description="Optional context")


class WorkflowRequest(BaseModel):
    """Schema for multi-agent workflow request."""
    content: str = Field(..., description="User input for the workflow")


class AgentInfo(BaseModel):
    """Schema for agent information."""
    name: str
    description: str
    role: str
    model: str
    temperature: float
    max_tokens: int


class AgentsListResponse(BaseModel):
    """Schema for list of available agents."""
    pass  # This will accept any dict structure
    
    model_config = {"extra": "allow"}


class AgentResponse(BaseModel):
    """Schema for single agent response."""
    agent_role: str
    response: str
    model_used: str
    timestamp: Optional[str] = None
    
    model_config = {"protected_namespaces": ()}


class AgentTeamResponse(BaseModel):
    """Schema for multi-agent team response."""
    agents_used: List[str]
    outputs: Dict[str, str]
    timestamp: Optional[str] = None
    
    model_config = {"protected_namespaces": ()}


class WorkflowNode(BaseModel):
    """Schema for a workflow execution node."""
    agent: str
    output: Optional[str] = None
    outputs: Optional[Dict[str, str]] = None
    feedback: Optional[str] = None
    timestamp: str


class WorkflowResponse(BaseModel):
    """Schema for complete workflow response."""
    user_input: str
    coordinator_task: Optional[str]
    task_breakdown: Optional[List[str]]
    specialist_outputs: Dict[str, str]
    evaluator_feedback: Optional[str]
    final_response: str
    workflow_history: List[WorkflowNode]
    
    model_config = {"protected_namespaces": ()}


class ThreadMessageWithAgents(BaseModel):
    """Schema for thread message processing with agents."""
    content: str = Field(..., description="User message")
    agent_roles: Optional[List[AgentRole]] = Field(
        None,
        description="Specific agents to use"
    )
    use_workflow: bool = Field(
        False,
        description="Use full multi-agent workflow"
    )
    context: Optional[Dict[str, Any]] = Field(None, description="Optional context")
