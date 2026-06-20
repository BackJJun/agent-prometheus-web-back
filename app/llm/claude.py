from langchain_anthropic import ChatAnthropic

from app.llm.llm_provider import LLMProvider


class ClaudeLLMProvider(LLMProvider):
    def _build_llm(self) -> ChatAnthropic:
        return ChatAnthropic(
            model=self.config.model,
            api_key=self.config.api_key,
            streaming=True,
        )
