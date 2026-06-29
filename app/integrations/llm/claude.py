import json
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from anthropic import AsyncAnthropic, APIConnectionError, RateLimitError, APIStatusError
from app.integrations.llm.base import BaseLLMService
from app.core.config import get_settings
from app.core.exception import LLMResponseParseException   # fixed typo
from app.core.logger import logger

settings = get_settings()


class ClaudeService(BaseLLMService):

    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = settings.anthropic_model
        self.max_tokens = settings.anthropic_max_tokens
        logger.info(f"ClaudeService initialized | model={self.model}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((APIConnectionError, RateLimitError)),
        reraise=True,
    )
    async def complete(self, system_prompt: str, user_message: str) -> str:
        """
        Calls Claude API with retry logic.
        Retries on: connection errors, rate limits
        Fails immediately on: auth errors, invalid requests
        """
        logger.debug(f"Calling Claude | model={self.model} | prompt_chars={len(user_message)}")

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        result = response.content[0].text
        logger.debug(f"Claude response received | chars={len(result)} | stop_reason={response.stop_reason}")
        return result

    async def complete_json(self, system_prompt: str, user_message: str) -> dict:
        """
        Calls Claude and parses response as JSON.
        Handles markdown code fences Claude sometimes adds.
        """
        raw = await self.complete(system_prompt, user_message)

        # Strip ```json ... ``` or ``` ... ``` fences
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            # Remove first line (```json or ```)
            cleaned = cleaned.split("\n", 1)[1]
            # Remove closing ```
            cleaned = cleaned.rsplit("```", 1)[0]

        cleaned = cleaned.strip()

        try:
            parsed = json.loads(cleaned)
            logger.debug(f"JSON parsed successfully | keys={list(parsed.keys())}")
            return parsed
        except json.JSONDecodeError as e:
            logger.error(
                f"JSON parse failed | error={e} | "
                f"raw_preview={raw[:300]}"
            )
            raise LLMResponseParseException(
                agent_name="claude",
                raw_response=raw,
            ) from e