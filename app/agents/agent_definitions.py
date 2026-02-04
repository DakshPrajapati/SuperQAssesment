"""
Agent definitions for the multi-agent system.
Defines different agent roles and their capabilities.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum
from app.core.models import ModelName


class AgentRole(str, Enum):
    """Enumeration of available agent roles."""
    COORDINATOR = "coordinator"
    SPECIALIST = "specialist"
    EVALUATOR = "evaluator"
    SUMMARIZER = "summarizer"
    RESEARCHER = "researcher"


@dataclass
class AgentConfig:
    """Configuration for an agent."""
    name: str
    role: AgentRole
    system_prompt: str
    model: ModelName  # Use ModelName enum instead of string
    temperature: float = 0.7
    max_tokens: int = 1000
    description: str = ""


# Predefined agent configurations
COORDINATOR_AGENT = AgentConfig(
    name="Coordinator",
    role=AgentRole.COORDINATOR,
    model=ModelName.GPT_4_TURBO,
    system_prompt="""You are a coordinator agent. Your job is to:
1. Understand the user's request
2. Break down complex tasks into sub-tasks
3. Delegate to specialist agents
4. Synthesize responses from multiple agents
5. Ensure consistency across agent outputs

Be concise and focus on delegating work effectively.""",
    temperature=0.5,
    max_tokens=500,
    description="Orchestrates other agents and coordinates workflows"
)

SPECIALIST_AGENT = AgentConfig(
    name="Specialist",
    role=AgentRole.SPECIALIST,
    model=ModelName.MISTRAL_7B,
    system_prompt="""You are a specialist agent. Your job is to:
1. Focus on specific domains or tasks
2. Provide detailed, expert-level responses
3. Handle complex problem-solving
4. Suggest improvements and optimizations

Be thorough and provide comprehensive analysis.""",
    temperature=0.7,
    max_tokens=1500,
    description="Provides specialized expertise on specific topics"
)

EVALUATOR_AGENT = AgentConfig(
    name="Evaluator",
    role=AgentRole.EVALUATOR,
    model=ModelName.GPT_4_TURBO,
    system_prompt="""You are an evaluator agent. Your job is to:
1. Review responses from other agents
2. Check for accuracy and quality
3. Identify inconsistencies or gaps
4. Provide critical feedback and improvements
5. Rate response quality on a scale

Be objective and fair in your evaluations.""",
    temperature=0.3,
    max_tokens=800,
    description="Evaluates and quality-checks agent outputs"
)

SUMMARIZER_AGENT = AgentConfig(
    name="Summarizer",
    role=AgentRole.SUMMARIZER,
    model=ModelName.GPT_35_TURBO,
    system_prompt="""You are a summarizer agent. Your job is to:
1. Extract key points from discussions
2. Create concise summaries
3. Highlight important decisions
4. Maintain context while being brief

Be concise and capture the essence.""",
    temperature=0.4,
    max_tokens=600,
    description="Summarizes conversations and extracts key information"
)

RESEARCHER_AGENT = AgentConfig(
    name="Researcher",
    role=AgentRole.RESEARCHER,
    model=ModelName.MISTRAL_7B,
    system_prompt="""You are a research agent. Your job is to:
1. Gather information on topics
2. Analyze different perspectives
3. Provide comprehensive background
4. Identify patterns and connections

Be thorough and cite your reasoning.""",
    temperature=0.6,
    max_tokens=1500,
    description="Researches topics and provides comprehensive analysis"
)

# Map of all agents
AVAILABLE_AGENTS = {
    AgentRole.COORDINATOR: COORDINATOR_AGENT,
    AgentRole.SPECIALIST: SPECIALIST_AGENT,
    AgentRole.EVALUATOR: EVALUATOR_AGENT,
    AgentRole.SUMMARIZER: SUMMARIZER_AGENT,
    AgentRole.RESEARCHER: RESEARCHER_AGENT,
}


@dataclass
class AgentState:
    """State passed through the agent workflow."""
    user_input: str
    agent_role: AgentRole
    context: Dict[str, Any]
    intermediate_outputs: Dict[str, str]
    final_output: Optional[str] = None
    agent_history: List[Dict[str, str]] = None
    
    def __post_init__(self):
        if self.agent_history is None:
            self.agent_history = []


@dataclass
class MultiAgentWorkflowState:
    """State for multi-agent workflows."""
    user_input: str
    coordinator_task: Optional[str] = None
    task_breakdown: Optional[List[str]] = None
    specialist_outputs: Dict[str, str] = None
    evaluator_feedback: Optional[str] = None
    final_response: Optional[str] = None
    workflow_history: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.specialist_outputs is None:
            self.specialist_outputs = {}
        if self.workflow_history is None:
            self.workflow_history = []
