from __future__ import annotations

import json
import logging

import anthropic

from mymovie.config import LLMConfig

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, config: LLMConfig):
        self.client = anthropic.AsyncAnthropic(
            api_key=config.api_key,
            base_url=config.base_url,
        )
        self.model = config.model
        self.max_tokens = config.max_tokens
        self.temperature = config.temperature

    async def chat(self, system: str, user: str, temperature: float | None = None) -> str:
        """Simple chat completion. Returns the text response."""
        temp = temperature if temperature is not None else self.temperature
        for attempt in range(3):
            try:
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=temp,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                )
                return response.content[0].text
            except (anthropic.RateLimitError, anthropic.APIStatusError, anthropic.APIConnectionError) as e:
                logger.warning(f"LLM call attempt {attempt + 1} failed: {e}")
                if attempt < 2:
                    import asyncio
                    await asyncio.sleep(3 * (2 ** attempt))
                else:
                    raise

    async def chat_json(self, system: str, user: str, temperature: float | None = None) -> dict:
        """Chat completion that expects JSON output. Parses and returns dict."""
        full_system = system + "\n\nYou MUST respond with valid JSON only. No markdown, no explanation, just the JSON object."
        for attempt in range(3):
            text = await self.chat(full_system, user, temperature)
            try:
                # Try to extract JSON from potential markdown code blocks
                cleaned = text.strip()
                if cleaned.startswith("```"):
                    lines = cleaned.split("\n")
                    # Remove first and last lines (code block markers)
                    lines = [l for l in lines if not l.strip().startswith("```")]
                    cleaned = "\n".join(lines)
                return json.loads(cleaned)
            except json.JSONDecodeError:
                logger.warning(f"LLM returned invalid JSON on attempt {attempt + 1}, retrying with error context")
                if attempt < 2:
                    full_system = system + "\n\nYour previous response was not valid JSON. Please respond with ONLY valid JSON, no markdown formatting."
                else:
                    raise ValueError(f"LLM failed to return valid JSON after 3 attempts. Last response: {text[:500]}")

    async def chat_messages(self, system: str, messages: list[dict], temperature: float | None = None) -> str:
        """Multi-turn chat completion. Messages should be [{"role": "user"|"assistant", "content": "..."}]."""
        temp = temperature if temperature is not None else self.temperature
        for attempt in range(3):
            try:
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=temp,
                    system=system,
                    messages=messages,
                )
                return response.content[0].text
            except (anthropic.RateLimitError, anthropic.APIStatusError, anthropic.APIConnectionError) as e:
                logger.warning(f"LLM call attempt {attempt + 1} failed: {e}")
                if attempt < 2:
                    import asyncio
                    await asyncio.sleep(3 * (2 ** attempt))
                else:
                    raise
