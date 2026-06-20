from collections.abc import AsyncIterator
from dataclasses import dataclass

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage


@dataclass(frozen=True)
class LLMProviderConfig:
    provider: str
    model: str
    base_url: str | None = None
    api_key: str | None = None


class LLMProvider:
    def __init__(self, config: LLMProviderConfig) -> None:
        self.config = config

    def _messages(self, prompt: str) -> list[BaseMessage]:
        return [
            SystemMessage(
                content=(
                    "You are Prometheus, a concise Korean AI assistant. "
                    "Always answer in valid Markdown."
                )
            ),
            HumanMessage(content=prompt),
        ]

    async def stream_markdown(self, prompt: str) -> AsyncIterator[str]:
        llm = self._build_llm()
        async for chunk in llm.astream(self._messages(prompt)):
            content = getattr(chunk, "content", "")
            if isinstance(content, str) and content:
                yield content
            elif isinstance(content, list):
                text = "".join(
                    item.get("text", "") for item in content if isinstance(item, dict)
                )
                if text:
                    yield text

    def _build_llm(self):
        raise NotImplementedError
