"""
NVIDIA NIM (Kimi) LLM Service Integration.
Implements the abstract BaseLLMService using the OpenAI client pointed to the NVIDIA API gateway.
"""
import asyncio
import json
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from openai import AsyncOpenAI, APIConnectionError, RateLimitError
from app.integrations.llm.base import BaseLLMService
from app.core.config import get_settings
from app.core.exception import LLMResponseParseException
from app.core.logger import logger

settings = get_settings()


class NvidiaService(BaseLLMService):
    """
    Service client for interacting with NVIDIA NIM API.
    Specifically optimized for Moonshot Kimi models.
    """
    # Shared lock defined at class level, instantiated lazily inside the active event loop
    _lock = None

    def __init__(self):
        if NvidiaService._lock is None:
            NvidiaService._lock = asyncio.Lock()
            
        # We route through NVIDIA's OpenAI-compatible API endpoint
        self.client = AsyncOpenAI(
            api_key=settings.nvidia_api_key,
            base_url="https://integrate.api.nvidia.com/v1"
        )
        self.model = settings.nvidia_model
        self.max_tokens = 16384  # Kimi supports larger context limits
        logger.info(f"NvidiaService initialized | model={self.model}")

    async def complete(self, system_prompt: str, user_message: str) -> str:
        """
        Sends a completion request to the NVIDIA NIM endpoint.
        Uses class-level lock and a sleep delay to avoid concurrent rate limits.
        """
        async with self._lock:
            # Add a 30s delay between requests to guarantee we stay under the strict 2 RPM rate limit of NVIDIA NIM free tier
            await asyncio.sleep(30.0)
            return await self._execute_complete(system_prompt, user_message)

    @retry(
        stop=stop_after_attempt(6),
        wait=wait_exponential(multiplier=2, min=4, max=20),
        retry=retry_if_exception_type((APIConnectionError, RateLimitError)),
        reraise=True,
    )
    async def _execute_complete(self, system_prompt: str, user_message: str) -> str:
        logger.debug(f"Calling NVIDIA NIM | model={self.model} | prompt_chars={len(user_message)}")

        response = await self.client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_message},
            ],
            temperature=1.0,
            top_p=1.0,
        )

        result = response.choices[0].message.content
        finish_reason = response.choices[0].finish_reason
        logger.debug(f"NVIDIA NIM response received | chars={len(result)} | finish_reason={finish_reason}")
        return result

    async def complete_json(self, system_prompt: str, user_message: str) -> dict:
        """
        Requests a completion and parses the response as JSON.
        Handles cleaning markdown fences if the model wraps JSON in codeblocks.
        """
        logger.debug(f"Calling NVIDIA NIM for JSON | model={self.model}")

        # Explicitly instruct the system to respond in raw JSON
        system_instruction = system_prompt + "\nRespond strictly in valid JSON without any markdown formatting."
        raw = await self.complete(system_instruction, user_message)

        # Robust parsing cleanup to handle code block wrappers
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            # Strip off the leading ```json or ```
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:].strip()
            else:
                cleaned = cleaned[3:].strip()
            # Strip off the trailing ```
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()

        try:
            parsed = json.loads(cleaned)
            logger.debug(f"NVIDIA NIM JSON parsed | keys={list(parsed.keys())}")
            return parsed
        except json.JSONDecodeError as e:
            logger.error(f"NVIDIA NIM JSON parse failed | error={e} | raw={raw[:300]}")
            raise LLMResponseParseException(
                agent_name="nvidia",
                raw_response=raw,
            ) from e
