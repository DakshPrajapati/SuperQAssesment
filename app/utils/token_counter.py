"""
Token counter system for managing token usage and preventing context window overflow.
Provides utilities to count tokens for different models and validate against context limits.
"""

from typing import List, Dict, Any, Union
from app.core.models import ModelName, get_model_config, ModelConfig


class TokenCounter:
    """
    Token counter for estimating token usage across different models.
    Uses approximate token counting methods for different providers.
    """
    
    # Approximate tokens per word by provider
    TOKENS_PER_WORD = {
        "google": 1.3,
        "openai": 1.3,
        "mistralai": 1.3,
        "anthropic": 1.3,
    }
    
    # Additional overhead for system/formatting
    SYSTEM_OVERHEAD = 50
    MESSAGE_OVERHEAD = 10  # per message
    
    @staticmethod
    def count_tokens(text: str, model_name: Union[str, ModelName]) -> int:
        """
        Count approximate tokens for a text input using a specific model.
        
        Args:
            text: Text to count tokens for
            model_name: Model name (string or ModelName enum)
            
        Returns:
            Approximate token count
        """
        if not text:
            return 0
        
        config = get_model_config(model_name)
        provider = config.provider.value
        
        # Estimate tokens based on word count
        word_count = len(text.split())
        tokens_per_word = TokenCounter.TOKENS_PER_WORD.get(provider, 1.3)
        estimated_tokens = int(word_count * tokens_per_word)
        
        return max(estimated_tokens, 1)
    
    @staticmethod
    def count_messages_tokens(
        messages: List[Dict[str, str]],
        model_name: Union[str, ModelName],
        system_prompt: str = ""
    ) -> int:
        """
        Count approximate tokens for a list of messages.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model_name: Model name
            system_prompt: Optional system prompt
            
        Returns:
            Total approximate token count
        """
        config = get_model_config(model_name)
        provider = config.provider.value
        tokens_per_word = TokenCounter.TOKENS_PER_WORD.get(provider, 1.3)
        
        total_tokens = TokenCounter.SYSTEM_OVERHEAD
        
        # Add system prompt tokens
        if system_prompt:
            system_tokens = int(len(system_prompt.split()) * tokens_per_word)
            total_tokens += system_tokens
        
        # Add message tokens with overhead
        for message in messages:
            if isinstance(message, dict) and "content" in message:
                content = message["content"]
                content_tokens = int(len(content.split()) * tokens_per_word)
                total_tokens += content_tokens + TokenCounter.MESSAGE_OVERHEAD
        
        return total_tokens
    
    @staticmethod
    def get_available_context(
        model_name: Union[str, ModelName],
        used_tokens: int
    ) -> int:
        """
        Get remaining available context tokens for a model.
        
        Args:
            model_name: Model name
            used_tokens: Number of tokens already used
            
        Returns:
            Remaining available tokens, or -1 if exceeds context window
        """
        config = get_model_config(model_name)
        remaining = config.context_window - used_tokens
        return remaining
    
    @staticmethod
    def validate_context(
        model_name: Union[str, ModelName],
        used_tokens: int,
        buffer: int = 100
    ) -> Dict[str, Any]:
        """
        Validate if token usage is within acceptable limits.
        
        Args:
            model_name: Model name
            used_tokens: Number of tokens used
            buffer: Safety buffer to reserve (default: 100 tokens)
            
        Returns:
            Dictionary with validation results:
            - is_valid: Whether usage is valid
            - used_tokens: Tokens currently used
            - max_tokens: Context window size
            - remaining: Remaining available tokens
            - safety_exceeded: Whether safety buffer is exceeded
            - percentage_used: Percentage of context used
        """
        config = get_model_config(model_name)
        remaining = config.context_window - used_tokens
        safety_exceeded = remaining <= buffer
        percentage_used = (used_tokens / config.context_window) * 100
        
        return {
            "is_valid": remaining > buffer,
            "used_tokens": used_tokens,
            "max_tokens": config.context_window,
            "remaining": max(remaining, 0),
            "safety_exceeded": safety_exceeded,
            "percentage_used": round(percentage_used, 2),
            "model": str(model_name) if isinstance(model_name, ModelName) else model_name,
        }


class ContextWindowManager:
    """
    Manages context window for ongoing conversations.
    Tracks token usage and provides warnings/guidance for context management.
    """
    
    def __init__(self, model_name: Union[str, ModelName], buffer: int = 500):
        """
        Initialize the context window manager.
        
        Args:
            model_name: Model name to manage context for
            buffer: Safety buffer to reserve (default: 500 tokens)
        """
        self.model_name = model_name
        self.config = get_model_config(model_name)
        self.buffer = buffer
        self.used_tokens = 0
        self.token_history = []
    
    def add_tokens(self, text: str, source: str = "message") -> int:
        """
        Add tokens from new text and track usage.
        
        Args:
            text: Text to count tokens for
            source: Source of the tokens (for tracking)
            
        Returns:
            Number of tokens added
        """
        tokens = TokenCounter.count_tokens(text, self.model_name)
        self.used_tokens += tokens
        self.token_history.append({
            "source": source,
            "tokens": tokens,
            "cumulative": self.used_tokens
        })
        return tokens
    
    def reset(self):
        """Reset token counter and history."""
        self.used_tokens = 0
        self.token_history = []
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current context window status.
        
        Returns:
            Status dictionary with usage information
        """
        validation = TokenCounter.validate_context(
            self.model_name,
            self.used_tokens,
            self.buffer
        )
        
        return {
            **validation,
            "buffer": self.buffer,
            "tokens_to_safety": max(0, self.buffer - validation["remaining"]),
            "history_length": len(self.token_history),
        }
    
    def is_safe(self) -> bool:
        """Check if current usage is within safe limits."""
        remaining = self.config.context_window - self.used_tokens
        return remaining > self.buffer
    
    def get_available_tokens(self) -> int:
        """Get remaining available tokens (accounting for buffer)."""
        remaining = self.config.context_window - self.used_tokens
        return max(0, remaining - self.buffer)
    
    def can_fit(self, text: str) -> bool:
        """
        Check if new text can fit within context window.
        
        Args:
            text: Text to check
            
        Returns:
            True if text can fit within safe limits
        """
        tokens_needed = TokenCounter.count_tokens(text, self.model_name)
        available = self.get_available_tokens()
        return tokens_needed <= available
    
    def warn_if_approaching_limit(self) -> str:
        """
        Generate warning message if approaching context limit.
        
        Returns:
            Warning message, or empty string if no warning needed
        """
        status = self.get_status()
        percentage = status["percentage_used"]
        
        if percentage >= 90:
            return f"⚠️ CRITICAL: {percentage}% of context window used. Only {status['remaining']} tokens remaining."
        elif percentage >= 75:
            return f"⚠️ WARNING: {percentage}% of context window used. {status['remaining']} tokens remaining."
        elif percentage >= 50:
            return f"ℹ️ INFO: {percentage}% of context window used."
        
        return ""


# Module-level convenience function
def count_tokens(text: str, model_name: Union[str, ModelName]) -> int:
    """
    Convenience function to count tokens for text.
    
    Args:
        text: Text to count tokens for
        model_name: Model name
        
    Returns:
        Approximate token count
    """
    return TokenCounter.count_tokens(text, model_name)


def validate_context(model_name: Union[str, ModelName], used_tokens: int) -> Dict[str, Any]:
    """
    Convenience function to validate context usage.
    
    Args:
        model_name: Model name
        used_tokens: Number of tokens used
        
    Returns:
        Validation results
    """
    return TokenCounter.validate_context(model_name, used_tokens)
