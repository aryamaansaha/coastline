"""
LLM Provider Wrapper

Provides a unified interface for switching between LLM providers
Configuration via environment variables:
- LLM_PROVIDER: "openai" | "anthropic" | "google" (default: "openai")
- LLM_MODEL: Model name (default depends on provider)
- LLM_TEMPERATURE: Temperature (default: 0)
"""

import os
from typing import Literal
from langchain_core.language_models.chat_models import BaseChatModel


# Type aliases
Provider = Literal["openai", "anthropic", "google"]

# Default models per provider
DEFAULT_MODELS = {
    "openai": "gpt-5.1",
    "anthropic": "claude-sonnet-4-5",
    "google": "gemini-2.5-pro",
}


def get_llm(
    provider: Provider | None = None,
    model: str | None = None,
    temperature: float | None = None,
) -> BaseChatModel:
    """
    Get an LLM instance based on provider and model.
    
    Args:
        provider: LLM provider ("openai", "anthropic", "google")
                  Defaults to LLM_PROVIDER env var or "openai"
        model: Model name. Defaults to LLM_MODEL env var or provider's default
        temperature: Temperature for sampling. Defaults to LLM_TEMPERATURE env var or 0
    
    Returns:
        BaseChatModel instance ready for use with LangChain/LangGraph
    
    Example:
        # Use defaults from environment
        llm = get_llm()
        
        # Override provider/model
        llm = get_llm(provider="anthropic", model="claude-3-haiku-20240307")
    """
    # Resolve configuration
    provider = provider or os.getenv("LLM_PROVIDER", "openai").lower()
    temperature = temperature if temperature is not None else float(os.getenv("LLM_TEMPERATURE", "0"))
    
    # Validate provider
    if provider not in DEFAULT_MODELS:
        raise ValueError(f"Unknown provider: {provider}. Must be one of: {list(DEFAULT_MODELS.keys())}")
    
    # Resolve model (use provided, env var, or default for provider)
    model = model or os.getenv("LLM_MODEL") or DEFAULT_MODELS[provider]
    
    # Create LLM based on provider
    if provider == "openai":
        return _get_openai(model, temperature)
    elif provider == "anthropic":
        return _get_anthropic(model, temperature)
    elif provider == "google":
        return _get_google(model, temperature)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def _get_openai(model: str, temperature: float) -> BaseChatModel:
    """Get OpenAI chat model."""
    from langchain_openai import ChatOpenAI
    
    return ChatOpenAI(
        model=model,
        temperature=temperature,
    )


def _get_anthropic(model: str, temperature: float) -> BaseChatModel:
    """Get Anthropic chat model."""
    try:
        from langchain_anthropic import ChatAnthropic
    except ImportError:
        raise ImportError(
            "langchain-anthropic is required for Anthropic models. "
            "Install with: pip install langchain-anthropic"
        )
    
    return ChatAnthropic(
        model=model,
        temperature=temperature,
    )


def _get_google(model: str, temperature: float) -> BaseChatModel:
    """Get Google chat model."""
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError:
        raise ImportError(
            "langchain-google-genai is required for Google models. "
            "Install with: pip install langchain-google-genai"
        )
    
    return ChatGoogleGenerativeAI(
        model=model,
        temperature=temperature,
    )


# Convenience function to get current config
def get_llm_config() -> dict:
    """Get current LLM configuration from environment."""
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    return {
        "provider": provider,
        "model": os.getenv("LLM_MODEL") or DEFAULT_MODELS.get(provider, "unknown"),
        "temperature": float(os.getenv("LLM_TEMPERATURE", "0")),
    }

