from langchain_openai import ChatOpenAI

from app.llm.llm_provider import LLMProvider


class OpenAILLMProvider(LLMProvider):
    def _build_llm(self) -> ChatOpenAI:
        return ChatOpenAI(
            model=self.config.model,
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            streaming=True,
        )
