from langchain_groq import ChatGroq
from langchain_community.chat_models import ChatOllama
from app.core.config import settings

def get_llm(temperature: float = 0.2, json_mode: bool = False):
    """
    Model client factory. Returns ChatGroq (fast cloud model) or ChatOllama (free local model).
    
    Example Usage:
        llm = get_llm(temperature=0.3, json_mode=True)
        response = llm.invoke("Generate a tourist route...")
    """
    provider = settings.LLM_PROVIDER.lower()
    
    if provider == "groq":
        # Enforce that Groq key must exist
        if not settings.GROQ_API_KEY or "your_groq_key" in settings.GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY is missing or invalid. "
                "Please configure it in the .env file at the project root."
            )
            
        model_kwargs = {}
        if json_mode:
            # Configures Groq's API to strictly return valid JSON structures
            model_kwargs = {"response_format": {"type": "json_object"}}
            
        return ChatGroq(
            groq_api_key=settings.GROQ_API_KEY,
            model_name=settings.GROQ_MODEL,
            temperature=temperature,
            model_kwargs=model_kwargs
        )
        
    elif provider == "ollama":
        print(f"Loading local Ollama model: {settings.OLLAMA_MODEL}...")
        return ChatOllama(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            temperature=temperature
        )
        
    else:
        raise ValueError(
            f"Unsupported LLM_PROVIDER: '{provider}'. "
            "Please edit your .env file to choose 'groq' or 'ollama'."
        )
