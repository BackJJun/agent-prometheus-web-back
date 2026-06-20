from collections.abc import AsyncIterator

from app.llm.llm_provider import LLMProvider


class FallbackLLMProvider(LLMProvider):
    async def stream_markdown(self, prompt: str) -> AsyncIterator[str]:
        response = (
            "## 답변\n\n"
            "현재 활성화된 LLM provider 설정이 없어 로컬 fallback 응답을 반환합니다.\n\n"
            f"- 요청: {prompt}\n"
            "- 실제 OpenAI, vLLM, Claude, Gemini 설정을 등록하면 "
            "LangChain streaming으로 응답합니다.\n"
        )
        for token in response.split(" "):
            yield token + " "

    def _build_llm(self):
        raise RuntimeError("Fallback provider does not build a LangChain model")
