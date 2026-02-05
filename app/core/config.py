"""
Configuration settings for the chat service application.
Reads settings from environment variables using Pydantic settings.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    database_url: str
    openrouter_api_key: str
    summarization_model: str = "openai/gpt-3.5-turbo"
    default_llm_1: str = "openai/gpt-3.5-turbo"
    default_llm_2: str = "mistralai/mistral-7b-instruct"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
