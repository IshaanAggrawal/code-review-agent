from abc import ABC, abstractmethod


class BaseLLMService(ABC):
    """
    Abstract base — every LLM provider must implement this.
    Swap Claude → OpenAI by changing one line in builder.py.
    """

    @abstractmethod
    async def complete(self, system_prompt: str, user_message: str) -> str:
        """Returns raw text response."""
        pass

    @abstractmethod
    async def complete_json(self, system_prompt: str, user_message: str) -> dict:
        """Returns parsed JSON dict. Raises LLMResponseParseException on failure."""
        pass