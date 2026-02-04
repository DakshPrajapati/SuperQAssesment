"""
Thread Service for managing chat thread operations.
Orchestrates message processing, LLM interaction, and summarization.
"""

from sqlalchemy.orm import Session
from app.core.models import get_model_config, get_summary_size_for_model
from app.utils.token_counter import count_tokens
from app.crud import thread_crud
from app.services.llm_service import LLMService
from app.services.summarization_service import SummarizationService
from app.schemas.message_schemas import MessageResponse
from typing import List, Optional


class ThreadService:
    """
    Service for managing thread operations.
    
    Handles the orchestration of message processing, LLM interaction,
    and automatic conversation summarization.
    """
    
    SUMMARIZATION_THRESHOLD = 4  # Summarize after every 4 messages
    
    def __init__(self):
        """Initialize the Thread Service."""
        self.llm_service = LLMService()
        self.summarization_service = SummarizationService(self.llm_service)
    
    async def process_user_message(
        self,
        db: Session,
        thread_id: int,
        sender: str,
        user_message: str,
        model: str
    ) -> MessageResponse:
        """
        Process a user message and generate an agent response.
        
        This method:
        1. Retrieves the thread context (system prompt, summaries, messages)
        2. Calls the LLM to generate a response
        3. Saves both user and agent messages to the database
        4. Triggers auto-summarization if needed
        
        Args:
            db: Database session
            thread_id: ID of the thread
            sender: Name of the user sending the message
            user_message: The user's message content
            model: LLM model to use for response (e.g., "google/gemini-pro")
            
        Returns:
            MessageResponse with the generated agent response
            
        Raises:
            Exception: If thread not found or processing fails
        """

        user_msg_len = count_tokens(user_message, model)
        max_tokens = get_model_config(model).max_tokens
        if user_msg_len > max_tokens:
            raise ValueError(
                f"ERROR_MSG_TOO_LONG: user message tokens ({user_msg_len}) exceed model max_tokens ({max_tokens})"
            )
        # Get the thread
        thread = thread_crud.get_thread(db, thread_id)
        if not thread:
            raise Exception(f"Thread {thread_id} not found")
        
        # Save user message
        user_msg = thread_crud.add_message_to_thread(
            db=db,
            thread_id=thread_id,
            sender=sender,
            role="user",
            content=user_message
        )
        
        # Get conversation context
        recent_messages = thread_crud.get_messages_for_thread(
            db=db,
            thread_id=thread_id,
            exclude_before_summary=True
        )
        
        # Get last summary for context
        last_summary = thread_crud.get_last_summary_for_thread(db, thread_id)
        # Protect against no previous summary (None)
        if last_summary and getattr(last_summary, "summary_data", None):
            print(last_summary.summary_data)
        else:
            print("!!!!!!!!")
        # Get model metadata to determine message limits based on summary type
        summary_type = get_summary_size_for_model(model).value or "medium"
        
        # Define message limits per summary type
        message_limits = {
            "small": 2,      # Minimal context for token-constrained models
            "medium": 5,     # Balanced context for most models
            "large": 10      # Full context for capable models
        }
        max_messages = message_limits.get(summary_type, 5)
        limited_messages = recent_messages[-max_messages:] if recent_messages else []
        
        # Format messages for LLM
        messages_for_llm = []
        
        # Include system prompt if available (max 250 tokens)
        if thread.system_prompt:
            system_prompt_tokens = count_tokens(thread.system_prompt, model)
            MAX_SYSTEM_PROMPT_TOKENS = 250
            
            if system_prompt_tokens > MAX_SYSTEM_PROMPT_TOKENS:
                # Truncate system prompt to fit within token limit
                words = thread.system_prompt.split()
                truncated_prompt = ""
                for word in words:
                    test_prompt = truncated_prompt + " " + word if truncated_prompt else word
                    if count_tokens(test_prompt, model) <= MAX_SYSTEM_PROMPT_TOKENS:
                        truncated_prompt = test_prompt
                    else:
                        break
                system_prompt_to_use = truncated_prompt
            else:
                system_prompt_to_use = thread.system_prompt
            
            messages_for_llm.append({
                "role": "system",
                "content": system_prompt_to_use
            })
        
        # Include last summary as context if available
        if last_summary:
            from app.services.summary_utils import summary_data_to_text, SummarySlicingEngine
            try:
                sliced = SummarySlicingEngine.get_summary_for_model(last_summary, model)
            except Exception:
                sliced = last_summary.summary_data

            messages_for_llm.append({
                "role": "assistant",
                "content": f"[Previous Summary]\n{summary_data_to_text(sliced)}"
            })
        
        # Add limited recent messages based on model type
        for msg in limited_messages:
            messages_for_llm.append({
                "role": "user" if msg.role == "user" else "assistant",
                "content": msg.content
            })
        
        # Add the current user message
        messages_for_llm.append({
            "role": "user",
            "content": user_message
        })
        
        # Generate response from LLM
        try:
            print("MODEL:", model)
            print("SUMMARY TYPE:", summary_type)
            print("MAX MESSAGES:", max_messages)
            print("SYSTEM PROMPT:", thread.system_prompt)
            print("MESSAGES FOR LLM:")
            for msg in messages_for_llm:
                print(msg)

            agent_response, token_info = await self.llm_service.generate_response(
                model=model.strip(),
                system_prompt=thread.system_prompt,
                messages=messages_for_llm
            )
        except Exception as e:
            raise Exception(f"Failed to generate LLM response: {str(e)}")
        
        # Save agent response (use response text, not the token_info)
        agent_msg = thread_crud.add_message_to_thread(
            db=db,
            thread_id=thread_id,
            sender="Agent",
            role="agent",
            content=agent_response,
            model_used=model
        )
        
        # Check if we should summarize
        total_messages = len(recent_messages) + 2  # +2 for user and agent messages just added
        if total_messages >= self.SUMMARIZATION_THRESHOLD:
            print("[][][] need to summarize")
            await self._trigger_summarization(db, thread_id)
        
        return MessageResponse.model_validate(agent_msg)
    
    async def _trigger_summarization(self, db: Session, thread_id: int):
        """
        Trigger conversation summarization.
        
        Args:
            db: Database session
            thread_id: ID of the thread
        """
        try:
            # Get all messages for summarization
            messages = thread_crud.get_messages_for_thread(
                db=db,
                thread_id=thread_id,
                exclude_before_summary=True
            )
            
            if not messages:
                print("Cant find messages for summarization")
                return
            
            # Get last summary for context
            last_summary = thread_crud.get_last_summary_for_thread(db, thread_id)
            
            # Format messages for summarization
            formatted_messages = [
                {
                    "sender": msg.sender,
                    "role": msg.role,
                    "content": msg.content
                }
                for msg in messages
            ]

            # Generate structured summary
            summary_data = await self.summarization_service.summarize_conversation(
                messages=formatted_messages,
                previous_summary=last_summary.summary_data if last_summary else None
            )
            # Save summary with structured data
            thread_crud.add_summary_to_thread(
                db=db,
                thread_id=thread_id,
                summary_data=summary_data,
                message_count=len(messages)
            )
            
        except Exception as e:
            # Log the error but don't fail the main operation
            print(f"Summarization error for thread {thread_id}: {str(e)}")
    
    def close(self):
        """Close all services."""
        self.llm_service.close()
        self.summarization_service.close()
