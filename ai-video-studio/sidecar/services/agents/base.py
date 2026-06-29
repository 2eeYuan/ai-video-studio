"""
Base Agent class for the multi-stage video creation pipeline.
"""
import json
import re
from abc import ABC, abstractmethod
from typing import Any, Optional
from loguru import logger


class BaseAgent(ABC):
    """Base class for all agents in the pipeline."""

    name: str = "base"
    system_prompt: str = ""

    @abstractmethod
    async def execute(self, input_data: dict) -> dict:
        """Execute the agent's task and return structured output."""
        ...

    async def call_llm(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: str = "json",
    ) -> dict | str:
        """Call LLM and optionally parse JSON response."""
        from services.llm_service import call_llm

        messages = []
        if system_prompt or self.system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt or self.system_prompt,
            })
        messages.append({"role": "user", "content": user_prompt})

        raw = await call_llm(messages, temperature=temperature, max_tokens=max_tokens)

        if response_format == "json":
            return self._parse_json(raw)
        return raw

    def _parse_json(self, text: str) -> dict:
        """Extract JSON from LLM response, handling markdown code blocks."""
        # Try direct parse first
        text = text.strip()
        if text.startswith("{") or text.startswith("["):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass

        # Try extracting from markdown code block
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Try finding JSON object/array in text
        for pattern in [r"\{.*\}", r"\[.*\]"]:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    continue

        logger.warning(f"Failed to parse JSON from LLM response: {text[:200]}...")
        raise ValueError(f"LLM did not return valid JSON. Response: {text[:500]}")
