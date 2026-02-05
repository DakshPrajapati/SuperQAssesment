"""
Model registry and definitions for LLM providers.
Centralized management of all available models.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Literal


class ModelProvider(str, Enum):
    """LLM provider names."""
    GOOGLE = "google"
    OPENAI = "openai"
    MISTRAL = "mistralai"
    ANTHROPIC = "anthropic"
    UPSTAGE = "upstage"


class ModelName(str, Enum):
    """Available LLM models."""
    # OpenAI models
    GPT_4 = "openai/gpt-4"
    GPT_4_TURBO = "openai/gpt-4-turbo-preview"
    GPT_35_TURBO = "openai/gpt-3.5-turbo"
    
    # Mistral models
    MISTRAL_7B = "mistralai/mistral-7b-instruct"
    
    # Anthropic models
    CLAUDE_HAIKU = "anthropic/claude-3-haiku"

    SOLAR_PRO = "upstage/solar-pro-3:free"
    
class SummarySize(str, Enum):
    """Summary size categories for different model contexts."""
    SMALL = "small"      # ~100-200 tokens
    MEDIUM = "medium"    # ~300-500 tokens
    LARGE = "large"      # ~600-1000 tokens


@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    name: ModelName
    provider: ModelProvider
    max_tokens: int
    temperature: float = 0.7
    supports_vision: bool = False
    supports_function_calling: bool = False
    context_window: int = 4096  # tokens
    cost_per_1k_input: float = 0.0  # USD
    cost_per_1k_output: float = 0.0  # USD
    preferred_summary_size: SummarySize = SummarySize.MEDIUM
    description: str = ""


# Model configurations registry
MODEL_CONFIGS = {
    ModelName.GPT_4: ModelConfig(
        name=ModelName.GPT_4,
        provider=ModelProvider.OPENAI,
        max_tokens=8192,
        temperature=0.7,
        supports_function_calling=True,
        context_window=8192,
        cost_per_1k_input=0.03,
        cost_per_1k_output=0.06,
        preferred_summary_size=SummarySize.LARGE,
        description="OpenAI's most capable model with excellent reasoning"
    ),
    ModelName.SOLAR_PRO: ModelConfig(
        name=ModelName.SOLAR_PRO,
        provider=ModelProvider.UPSTAGE,
        max_tokens=8192,
        temperature=0.7,
        supports_function_calling=True,
        context_window=8192,
        cost_per_1k_input=0.03,
        cost_per_1k_output=0.06,
        preferred_summary_size=SummarySize.LARGE,
        description="Upstage"
    ),
    ModelName.GPT_4_TURBO: ModelConfig(
        name=ModelName.GPT_4_TURBO,
        provider=ModelProvider.OPENAI,
        max_tokens=4096,
        temperature=0.7,
        supports_function_calling=True,
        context_window=128000,
        cost_per_1k_input=0.01,
        cost_per_1k_output=0.03,
        preferred_summary_size=SummarySize.LARGE,
        description="OpenAI's fast GPT-4 variant with expanded context"
    ),
    ModelName.GPT_35_TURBO: ModelConfig(
        name=ModelName.GPT_35_TURBO,
        provider=ModelProvider.OPENAI,
        max_tokens=4096,
        temperature=0.7,
        supports_function_calling=True,
        context_window=4096,
        cost_per_1k_input=0.0005,
        cost_per_1k_output=0.0015,
        preferred_summary_size=SummarySize.MEDIUM,
        description="OpenAI's fast and cost-effective model"
    ),
    ModelName.MISTRAL_7B: ModelConfig(
        name=ModelName.MISTRAL_7B,
        provider=ModelProvider.MISTRAL,
        max_tokens=1500,
        temperature=0.7,
        context_window=32000,
        preferred_summary_size=SummarySize.MEDIUM,
        description="Mistral's open-source 7B parameter model"
    ),
    ModelName.CLAUDE_HAIKU: ModelConfig(
        name=ModelName.CLAUDE_HAIKU,
        provider=ModelProvider.ANTHROPIC,
        max_tokens=1024,
        temperature=0.7,
        context_window=200000,
        preferred_summary_size=SummarySize.SMALL,
        description="Anthropic's fast and compact Claude model"
    ),
}



def get_model_config(model_name: str) -> ModelConfig:
    """
    Get configuration for a model by name.
    
    Args:
        model_name: Model name (can be ModelName enum or string)
        
    Returns:
        ModelConfig for the specified model
        
    Raises:
        ValueError: If model not found in registry
    """
    try:
        # Try to convert string to enum
        if isinstance(model_name, str):
            model = ModelName(model_name)
        else:
            model = model_name
        
        if model in MODEL_CONFIGS:
            return MODEL_CONFIGS[model]
        raise ValueError(f"Model {model} not found in registry")
    except (ValueError, KeyError):
        raise ValueError(f"Unknown model: {model_name}. Available models: {[m.value for m in ModelName]}")


def get_summary_size_for_model(model_name: str) -> SummarySize:
    """Get preferred summary size for a model."""
    config = get_model_config(model_name)
    return config.preferred_summary_size


def get_available_models() -> dict:
    """Get all available models with their configurations."""
    return {
        model.value: {
            "provider": config.provider.value,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "supports_vision": config.supports_vision,
            "supports_function_calling": config.supports_function_calling,
            "context_window": config.context_window,
            "preferred_summary_size": config.preferred_summary_size.value,
            "description": config.description
        }
        for model, config in MODEL_CONFIGS.items()
    }
