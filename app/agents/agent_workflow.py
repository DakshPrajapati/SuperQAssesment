"""
LangGraph-based multi-agent workflow system.
Manages coordination and communication between agents.
"""

from typing import Dict, Any, List, Optional
from langgraph.graph import StateGraph, END
from langchain.schema import HumanMessage, AIMessage, SystemMessage
import json

from app.agents.agent_definitions import (
    AgentState,
    MultiAgentWorkflowState,
    AgentRole,
    AVAILABLE_AGENTS,
)
from app.services.llm_service import LLMService


class AgentWorkflowEngine:
    """
    Orchestrates multi-agent workflows using LangGraph.
    
    Manages the flow of information between agents and ensures
    proper task delegation and coordination.
    """
    
    def __init__(self):
        """Initialize the workflow engine."""
        self.llm_service = LLMService()
        self.graph = None
        self._build_graph()
    
    def _build_graph(self):
        """Build the LangGraph state graph for agent coordination."""
        # Create state graph
        self.graph = StateGraph(MultiAgentWorkflowState)
        
        # Add nodes for different agent roles
        self.graph.add_node("coordinator", self._coordinator_node)
        self.graph.add_node("specialist", self._specialist_node)
        self.graph.add_node("evaluator", self._evaluator_node)
        self.graph.add_node("synthesizer", self._synthesizer_node)
        
        # Add entry point
        self.graph.set_entry_point("coordinator")
        
        # Add edges (transitions between nodes)
        self.graph.add_edge("coordinator", "specialist")
        self.graph.add_edge("specialist", "evaluator")
        self.graph.add_edge("evaluator", "synthesizer")
        self.graph.add_edge("synthesizer", END)
    
    async def _coordinator_node(self, state: MultiAgentWorkflowState) -> Dict[str, Any]:
        """
        Coordinator node: Break down user request into tasks.
        """
        agent_config = AVAILABLE_AGENTS[AgentRole.COORDINATOR]
        
        prompt = f"""User request: {state.user_input}

Please break this down into specific, actionable tasks for specialist agents.
Format your response as a JSON list with task descriptions."""
        
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        response = await self.llm_service.generate_response(
            model=agent_config.model,
            system_prompt=agent_config.system_prompt,
            messages=messages,
            temperature=agent_config.temperature,
            max_tokens=agent_config.max_tokens
        )
        
        # Parse task breakdown
        task_breakdown = self._extract_tasks(response)
        
        state.coordinator_task = response
        state.task_breakdown = task_breakdown
        state.workflow_history.append({
            "agent": "coordinator",
            "output": response,
            "timestamp": str(__import__('datetime').datetime.utcnow())
        })
        
        return state
    
    async def _specialist_node(self, state: MultiAgentWorkflowState) -> Dict[str, Any]:
        """
        Specialist node: Handle specific tasks.
        """
        agent_config = AVAILABLE_AGENTS[AgentRole.SPECIALIST]
        
        specialist_outputs = {}
        
        # Process each task
        for idx, task in enumerate(state.task_breakdown or []):
            prompt = f"""Original request: {state.user_input}

Task to handle: {task}

Please provide a detailed, expert response to this task."""
            
            messages = [
                {"role": "user", "content": prompt}
            ]
            
            response = await self.llm_service.generate_response(
                model=agent_config.model,
                system_prompt=agent_config.system_prompt,
                messages=messages,
                temperature=agent_config.temperature,
                max_tokens=agent_config.max_tokens
            )
            
            specialist_outputs[f"task_{idx}"] = response
        
        state.specialist_outputs = specialist_outputs
        state.workflow_history.append({
            "agent": "specialist",
            "outputs": specialist_outputs,
            "timestamp": str(__import__('datetime').datetime.utcnow())
        })
        
        return state
    
    async def _evaluator_node(self, state: MultiAgentWorkflowState) -> Dict[str, Any]:
        """
        Evaluator node: Review and critique specialist outputs.
        """
        agent_config = AVAILABLE_AGENTS[AgentRole.EVALUATOR]
        
        # Format specialist outputs for evaluation
        specialist_summary = "\n".join([
            f"Task {idx}: {output}"
            for idx, output in enumerate(state.specialist_outputs.values())
        ])
        
        prompt = f"""Original request: {state.user_input}

Specialist responses:
{specialist_summary}

Please evaluate the quality and completeness of these responses.
Provide constructive feedback and suggestions for improvement."""
        
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        feedback = await self.llm_service.generate_response(
            model=agent_config.model,
            system_prompt=agent_config.system_prompt,
            messages=messages,
            temperature=agent_config.temperature,
            max_tokens=agent_config.max_tokens
        )
        
        state.evaluator_feedback = feedback
        state.workflow_history.append({
            "agent": "evaluator",
            "feedback": feedback,
            "timestamp": str(__import__('datetime').datetime.utcnow())
        })
        
        return state
    
    async def _synthesizer_node(self, state: MultiAgentWorkflowState) -> Dict[str, Any]:
        """
        Synthesizer node: Combine all outputs into final response.
        """
        # Combine all agent outputs
        combined_input = f"""Original request: {state.user_input}

Specialist responses:
{chr(10).join([f"{k}: {v}" for k, v in state.specialist_outputs.items()])}

Evaluator feedback:
{state.evaluator_feedback}

Please synthesize all this information into a comprehensive, coherent final response."""
        
        messages = [
            {"role": "user", "content": combined_input}
        ]
        
        final_response = await self.llm_service.generate_response(
            model="google/gemini-pro",
            system_prompt="You are a master synthesizer. Combine all information into clear, coherent responses.",
            messages=messages,
            temperature=0.5,
            max_tokens=1500
        )
        
        state.final_response = final_response
        state.workflow_history.append({
            "agent": "synthesizer",
            "final_response": final_response,
            "timestamp": str(__import__('datetime').datetime.utcnow())
        })
        
        return state
    
    def _extract_tasks(self, response: str) -> List[str]:
        """
        Extract task list from coordinator response.
        """
        try:
            # Try to parse as JSON
            if "[" in response and "]" in response:
                json_str = response[response.index("["):response.rindex("]")+1]
                tasks = json.loads(json_str)
                return tasks if isinstance(tasks, list) else [response]
        except Exception:
            pass
        
        # Fallback: split by newlines
        lines = [line.strip() for line in response.split("\n") if line.strip()]
        return lines if lines else [response]
    
    async def execute_workflow(self, user_input: str) -> MultiAgentWorkflowState:
        """
        Execute the multi-agent workflow.
        
        Args:
            user_input: The user's input/request
            
        Returns:
            Final workflow state with all outputs
        """
        # Create initial state
        initial_state = MultiAgentWorkflowState(
            user_input=user_input,
            task_breakdown=[],
            specialist_outputs={},
            workflow_history=[]
        )
        
        # Execute each node
        state = await self._coordinator_node(initial_state)
        state = await self._specialist_node(state)
        state = await self._evaluator_node(state)
        state = await self._synthesizer_node(state)
        
        return state
    
    async def execute_single_agent(
        self,
        user_input: str,
        agent_role: AgentRole,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Execute a single agent workflow.
        
        Args:
            user_input: The user's input
            agent_role: Which agent to use
            context: Optional context information
            
        Returns:
            Agent's response
        """
        print(agent_role)
        agent_config = AVAILABLE_AGENTS.get(agent_role)
        print(agent_config)
        if not agent_config:
            raise ValueError(f"Unknown agent role: {agent_role}")
        
        # Build context into prompt if provided
        context_str = ""
        if context:
            context_str = f"Context: {json.dumps(context)}\n\n"
        
        messages = [
            {"role": "user", "content": f"{context_str}User input: {user_input}"}
        ]
        
        response = await self.llm_service.generate_response(
            model=agent_config.model,
            system_prompt=agent_config.system_prompt,
            messages=messages,
            temperature=agent_config.temperature,
            max_tokens=agent_config.max_tokens
        )
        
        return response
    
    def close(self):
        """Close the workflow engine and cleanup resources."""
        self.llm_service.close()
