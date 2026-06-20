from app.llm.claude import ClaudeLLMProvider
from app.llm.fallback import FallbackLLMProvider
from app.llm.gemini import GeminiLLMProvider
from app.llm.llm_provider import LLMProvider, LLMProviderConfig
from app.llm.openai import OpenAILLMProvider
from app.llm.vllm import VllmLLMProvider


def get_llm_provider(config: LLMProviderConfig | None) -> LLMProvider:
    if config is None:
        return FallbackLLMProvider(LLMProviderConfig(provider="fallback", model="fallback"))

    provider = config.provider.lower()
    fallback_config = LLMProviderConfig(provider="fallback", model="fallback")
    if provider == "openai":
        if not config.api_key:
            return FallbackLLMProvider(fallback_config)
        return OpenAILLMProvider(config)
    if provider == "vllm":
        if not config.base_url:
            return FallbackLLMProvider(fallback_config)
        return VllmLLMProvider(config)
    if provider in {"claude", "anthropic"}:
        if not config.api_key:
            return FallbackLLMProvider(fallback_config)
        return ClaudeLLMProvider(config)
    if provider in {"gemini", "google"}:
        if not config.api_key:
            return FallbackLLMProvider(fallback_config)
        return GeminiLLMProvider(config)
    return FallbackLLMProvider(fallback_config)
