from langchain_google_genai import ChatGoogleGenerativeAI

from app.llm.llm_provider import LLMProvider


class GeminiLLMProvider(LLMProvider):
    def _build_llm(self) -> ChatGoogleGenerativeAI:
        return ChatGoogleGenerativeAI(
            model=self.config.model,
            google_api_key=self.config.api_key,
            streaming=True,
        )
