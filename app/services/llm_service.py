"""
LLM Service for integrating with OpenRouter API.
Handles generation of responses from different LLM models.
Includes token counting and context window validation.
"""

import httpx
from typing import List, Dict, Any, Optional, Tuple
from app.core.config import settings
from app.utils.token_counter import TokenCounter, ContextWindowManager


class Message(Dict[str, str]):
    """Type alias for message dictionaries."""
    pass


class LLMService:
    """
    Service for interacting with OpenRouter API.
    
    Supports multiple LLM models and handles the complete interaction
    with the OpenRouter API for chat completions.
    Includes token counting and context window validation.
    """
    
    def __init__(self, api_key: str = None):
        """
        Initialize the LLM Service.
        
        Args:
            api_key: OpenRouter API key. If not provided, uses settings.
        """
        self.api_key = api_key or settings.openrouter_api_key
        self.base_url = "https://openrouter.ai/api/v1"
        self.client = httpx.Client(timeout=60.0)
        self.context_manager: Optional[ContextWindowManager] = None
    
    def filter_messages_by_length(
        self,
        messages: List[Message],
        max_message_length: int = 5000,
        max_char_length: Optional[int] = None
    ) -> Tuple[List[Message], Dict[str, Any]]:
        """
        Filter out messages that are too long.
        Removes messages exceeding length thresholds, prioritizing older messages.
        
        Args:
            messages: List of message dictionaries
            max_message_length: Maximum tokens per message (default: 5000)
            max_char_length: Maximum characters per message (optional)
            
        Returns:
            Tuple of (filtered messages, filter info dict with deleted count)
        """
        filtered = []
        deleted_count = 0
        deleted_content = []
        
        for msg in messages:
            content = msg.get("content", "")
            
            # Check character length if specified
            if max_char_length and len(content) > max_char_length:
                deleted_count += 1
                deleted_content.append(content[:100] + "...")
                continue
            
            # Check token length
            msg_tokens = TokenCounter.count_tokens(content, "openai/gpt-3.5-turbo")
            if msg_tokens > max_message_length:
                deleted_count += 1
                deleted_content.append(content[:100] + "...")
                continue
            
            filtered.append(msg)
        
        return filtered, {
            "deleted_count": deleted_count,
            "deleted_content": deleted_content,
            "remaining_count": len(filtered)
        }
    
    def trim_messages_to_context(
        self,
        messages: List[Message],
        model: str,
        system_prompt: str = "",
        reserve_tokens: int = 1000
    ) -> Tuple[List[Message], Dict[str, Any]]:
        """
        Trim messages from the beginning to fit within context window.
        Keeps the most recent messages and removes oldest ones if needed.
        
        Args:
            messages: List of messages to trim
            model: Model name
            system_prompt: System prompt (counts toward limit)
            reserve_tokens: Tokens to reserve for response (default: 1000)
            
        Returns:
            Tuple of (trimmed messages, trim info dict)
        """
        from app.core.models import get_model_config
        
        config = get_model_config(model)
        max_input_tokens = config.context_window - reserve_tokens
        
        # Count system prompt tokens
        system_tokens = TokenCounter.count_tokens(system_prompt, model) if system_prompt else 0
        available_tokens = max_input_tokens - system_tokens
        
        if available_tokens <= 0:
            return [], {
                "status": "error",
                "reason": "System prompt too large for context window",
                "system_tokens": system_tokens,
                "available_tokens": available_tokens
            }
        
        # Add messages from newest to oldest
        trimmed = []
        total_tokens = 0
        removed_count = 0
        
        # Process messages in reverse (newest first)
        for msg in reversed(messages):
            content = msg.get("content", "")
            msg_tokens = TokenCounter.count_tokens(content, model)
            
            if total_tokens + msg_tokens <= available_tokens:
                trimmed.insert(0, msg)  # Insert at beginning to maintain order
                total_tokens += msg_tokens
            else:
                removed_count += 1
        
        return trimmed, {
            "status": "trimmed",
            "messages_removed": removed_count,
            "messages_kept": len(trimmed),
            "tokens_used": system_tokens + total_tokens,
            "available_tokens": available_tokens,
            "tokens_used_by_messages": total_tokens
        }
    
    def clean_messages(
        self,
        messages: List[Message],
        model: str,
        system_prompt: str = "",
        max_message_length: int = 5000,
        reserve_tokens: int = 1000
    ) -> Tuple[List[Message], Dict[str, Any]]:
        """
        Clean and trim messages in one operation.
        First removes too-long messages, then trims to fit context.
        
        Args:
            messages: List of messages to clean
            model: Model name
            system_prompt: System prompt
            max_message_length: Max tokens per message
            reserve_tokens: Tokens to reserve for response
            
        Returns:
            Tuple of (cleaned messages, operation info)
        """
        # Step 1: Filter out too-long individual messages
        filtered, filter_info = self.filter_messages_by_length(
            messages,
            max_message_length=max_message_length
        )
        
        # Step 2: Trim to fit context window
        trimmed, trim_info = self.trim_messages_to_context(
            filtered,
            model,
            system_prompt,
            reserve_tokens
        )
        
        return trimmed, {
            "filtering": filter_info,
            "trimming": trim_info,
            "total_removed": filter_info["deleted_count"] + trim_info.get("messages_removed", 0)
        }

    async def generate_response(
        self,
        model: str,
        system_prompt: str,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        validate_tokens: bool = True,
        auto_trim: bool = True,
        max_message_length: int = 5000
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate a response from the specified LLM model.
        
        Args:
            model: Model identifier (e.g., "google/gemini-pro")
            system_prompt: System prompt to set the model's behavior
            messages: Conversation history as list of dicts with 'role' and 'content'
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens in the response
            validate_tokens: Whether to validate against context window (default: True)
            auto_trim: Whether to auto-trim messages if too long (default: True)
            max_message_length: Max tokens per message (default: 5000)
            
        Returns:
            Tuple of (generated response text, token usage info)
            
        Raises:
            Exception: If API call fails or token validation fails
        """
        # Initialize context manager if not already done
        if self.context_manager is None or self.context_manager.model_name != model:
            self.context_manager = ContextWindowManager(model, buffer=500)
        
        # Clean messages if auto_trim is enabled
        messages_to_use = messages
        cleaning_info = {}
        
        if auto_trim:
            messages_to_use, cleaning_info = self.clean_messages(
                messages,
                model,
                system_prompt,
                max_message_length=max_message_length,
                reserve_tokens=max_tokens
            )
        
        # Count tokens in the request
        input_tokens = TokenCounter.count_messages_tokens(
            messages_to_use,
            model,
            system_prompt
        )
        
        # Validate context if requested
        if validate_tokens:
            validation = TokenCounter.validate_context(model, input_tokens)
            if not validation["is_valid"]:
                raise Exception(
                    f"Token validation failed for model {model}. "
                    f"Used: {input_tokens} tokens, "
                    f"Available: {validation['remaining']} tokens. "
                    f"Cannot proceed with {max_tokens} output tokens."
                )
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "http://localhost",
            "X-Title": "Chat Service"
        }
        
        payload = {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                *messages_to_use
            ]
        }
        
        try:
            response = self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Extract the generated text
            if "choices" in result and len(result["choices"]) > 0:
                response_text = result["choices"][0]["message"]["content"]
                
                # Count output tokens
                output_tokens = TokenCounter.count_tokens(response_text, model)
                
                # Update context manager
                self.context_manager.add_tokens(response_text, source="response")
                
                # Get token usage info
                token_info = {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                    "context_status": self.context_manager.get_status(),
                    "warning": self.context_manager.warn_if_approaching_limit(),
                    "messages_cleaned": cleaning_info if cleaning_info else None
                }
                
                return response_text, token_info
            else:
                raise Exception(f"Unexpected API response format: {result}")
                
        except httpx.RequestError as e:
            raise Exception(f"API request failed: {str(e)}")
        except Exception as e:
            raise Exception(f"Error generating response: {str(e)}")
    
    def get_token_count(self, text: str, model: str) -> int:
        """
        Get token count for text without making API call.
        
        Args:
            text: Text to count tokens for
            model: Model name
            
        Returns:
            Approximate token count
        """
        return TokenCounter.count_tokens(text, model)
    
    def validate_context(self, model: str, used_tokens: int) -> Dict[str, Any]:
        """
        Validate token usage for a model.
        
        Args:
            model: Model name
            used_tokens: Number of tokens used
            
        Returns:
            Validation results
        """
        return TokenCounter.validate_context(model, used_tokens)
    
    def reset_context_manager(self):
        """Reset context manager token tracking."""
        if self.context_manager:
            self.context_manager.reset()
    
    def get_context_status(self, model: str) -> Optional[Dict[str, Any]]:
        """
        Get current context manager status.
        
        Args:
            model: Model name
            
        Returns:
            Context status or None if manager not initialized
        """
        if self.context_manager and self.context_manager.model_name == model:
            return self.context_manager.get_status()
        return None
    
    def close(self):
        """Close the HTTP client."""
        self.client.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
