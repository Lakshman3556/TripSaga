import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Explicitly find and load the .env file in the workspace root
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), '.env'))

class Settings(BaseSettings):
    """
    Settings class to parse and validate environment configurations.
    
    Example usage:
        from app.core.config import settings
        print(settings.LLM_PROVIDER) # Output: 'groq'
    """
    LLM_PROVIDER: str = "gemini"
    GROQ_API_KEY: str = ""
    OPENTRIPMAP_KEY: str = ""
    
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    

    class Config:
        # Pydantic configuration to read values from system env if set
        env_file = ".env"
        extra = "ignore"

# Global settings object to import across files
settings = Settings()
