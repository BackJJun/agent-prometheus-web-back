from langchain_openai import ChatOpenAI

from app.llm.llm_provider import LLMProvider


class VllmLLMProvider(LLMProvider):
    def _base_url(self) -> str | None:
        if not self.config.base_url:
            return None
        return self.config.base_url.removesuffix("/chat/completions")

    def _build_llm(self) -> ChatOpenAI:
        return ChatOpenAI(
            model=self.config.model,
            api_key=self.config.api_key or "vllm-local",
            base_url=self._base_url(),
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            streaming=True,
        )
