"""
Agents service for managing agent-based operations.
Provides high-level interface for agent coordination.
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from app.agents.agent_definitions import AgentRole, AVAILABLE_AGENTS
from app.agents.agent_workflow import AgentWorkflowEngine
from app.crud import thread_crud


class AgentsService:
    """
    Service for managing multi-agent interactions and workflows.
    
    Handles:
    - Single agent execution
    - Multi-agent workflows
    - Agent coordination
    - Result aggregation
    """
    
    def __init__(self):
        """Initialize the agents service."""
        self.workflow_engine = AgentWorkflowEngine()
    
    async def process_with_agent(
        self,
        user_input: str,
        agent_role: AgentRole,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Process user input with a specific agent.
        
        Args:
            user_input: The user's input
            agent_role: Which agent role to use
            context: Optional context information
            
        Returns:
            Agent's response
        """
        return await self.workflow_engine.execute_single_agent(
            user_input=user_input,
            agent_role=agent_role,
            context=context
        )
    
    async def process_with_workflow(self, user_input: str) -> Dict[str, Any]:
        """
        Process user input through complete multi-agent workflow.
        
        Coordinator breaks down task → Specialists handle tasks → 
        Evaluator reviews → Synthesizer creates final response
        
        Args:
            user_input: The user's input
            
        Returns:
            Dictionary with workflow results
        """
        state = await self.workflow_engine.execute_workflow(user_input)
        
        return {
            "user_input": state.user_input,
            "coordinator_task": state.coordinator_task,
            "task_breakdown": state.task_breakdown,
            "specialist_outputs": state.specialist_outputs,
            "evaluator_feedback": state.evaluator_feedback,
            "final_response": state.final_response,
            "workflow_history": state.workflow_history
        }
    
    async def process_with_agent_team(
        self,
        user_input: str,
        agent_roles: List[AgentRole],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Process with multiple specific agents.
        
        Useful when you want specific agents to handle different aspects
        of a problem in parallel or sequence.
        
        Args:
            user_input: The user's input
            agent_roles: List of agent roles to use
            context: Optional context
            
        Returns:
            Dictionary mapping agent roles to their outputs
        """
        results = {}
        
        for agent_role in agent_roles:
            response = await self.workflow_engine.execute_single_agent(
                user_input=user_input,
                agent_role=agent_role,
                context=context
            )
            results[agent_role.value] = response
        
        return results
    
    async def process_message_with_agents(
        self,
        db: Session,
        thread_id: int,
        user_input: str,
        agent_roles: Optional[List[AgentRole]] = None,
        use_workflow: bool = False
    ) -> Dict[str, Any]:
        """
        Process a message with agents and save results to thread.
        
        Args:
            db: Database session
            thread_id: Thread ID to save results to
            user_input: User's message
            agent_roles: Specific agents to use (if not using workflow)
            use_workflow: Whether to use full multi-agent workflow
            
        Returns:
            Processing results with agent outputs
        """
        # Get thread for context
        thread = thread_crud.get_thread(db, thread_id)
        if not thread:
            raise Exception(f"Thread {thread_id} not found")
        
        # Prepare context from thread
        context = {
            "thread_id": thread_id,
            "thread_title": thread.title,
            "system_prompt": thread.system_prompt
        }
        
        # Get last summary for additional context
        last_summary = thread_crud.get_last_summary_for_thread(db, thread_id)
        if last_summary:
            from app.services.summary_utils import summary_data_to_text
            context["last_summary"] = summary_data_to_text(last_summary.summary_data)
        
        # Process based on workflow type
        if use_workflow:
            results = await self.process_with_workflow(user_input)
            final_response = results.get("final_response", user_input)
        else:
            # Use specific agent roles or default to specialist
            if not agent_roles:
                agent_roles = [AgentRole.SPECIALIST]
            
            agent_outputs = await self.process_with_agent_team(
                user_input=user_input,
                agent_roles=agent_roles,
                context=context
            )
            
            results = {
                "user_input": user_input,
                "agent_outputs": agent_outputs,
                "agents_used": [role.value for role in agent_roles]
            }
            
            # Use first agent output as final response
            final_response = agent_outputs[agent_roles[0].value]
        
        # Save messages to database
        thread_crud.add_message_to_thread(
            db=db,
            thread_id=thread_id,
            sender="User",
            role="user",
            content=user_input
        )
        
        # Determine which agent produced the response
        agent_names = [role.value for role in (agent_roles or [AgentRole.SPECIALIST])]
        model_used = f"agents:{','.join(agent_names)}"
        
        thread_crud.add_message_to_thread(
            db=db,
            thread_id=thread_id,
            sender="MultiAgentTeam",
            role="agent",
            content=final_response,
            model_used=model_used
        )
        
        # Add workflow history to results
        results["saved_to_thread"] = True
        results["final_response"] = final_response
        
        return results
    
    def get_available_agents(self) -> Dict[str, Dict[str, str]]:
        """
        Get information about all available agents.
        
        Returns:
            Dictionary with agent information
        """
        agents_info = {}
        
        for role, config in AVAILABLE_AGENTS.items():
            agents_info[role.value] = {
                "name": config.name,
                "description": config.description,
                "role": config.role.value,
                "model": config.model,
                "temperature": config.temperature,
                "max_tokens": config.max_tokens
            }
        
        return agents_info
    
    def close(self):
        """Close the agents service."""
        self.workflow_engine.close()
