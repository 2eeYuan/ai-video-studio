"""
LLM service - generates video scripts and search terms.
Supports multiple providers via OpenAI-compatible API.
"""
import os
import json
import re
from typing import Optional
from loguru import logger

# Runtime config (updated via /config endpoint)
_runtime_config: dict = {}


def update_config(config: dict):
    """Update runtime configuration from frontend."""
    global _runtime_config
    _runtime_config = config
    logger.info(f"LLM config updated: provider={config.get('llm', {}).get('provider', 'default')}")


def _get_llm_config() -> tuple[str, str, str]:
    """Get LLM config: (api_key, base_url, model). Priority: runtime > env > default."""
    llm = _runtime_config.get("llm", {})
    api_key = llm.get("api_key") or os.environ.get("LLM_API_KEY", "")
    base_url = llm.get("base_url") or os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
    model = llm.get("model") or os.environ.get("LLM_MODEL", "gpt-4o-mini")
    return api_key, base_url, model


async def call_llm(
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    """Generic LLM call. Returns raw text response."""
    api_key, base_url, model = _get_llm_config()

    if not api_key:
        raise ValueError("未配置 LLM API Key，请在设置中配置")

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        raise


DEFAULT_SYSTEM_PROMPT = """你是一个专业的短视频文案编剧。请根据用户提供的主题，撰写适合短视频的旁白文案。

要求：
1. 第一人称视角，语气自然真实
2. 开头用悬念钩子吸引观众
3. 中间有具体细节和场景描写
4. 结尾留悬念或金句
5. 每段控制在50-80字
6. 使用合理的标点符号断句，有助于生成字幕

请直接输出文案内容，不要添加额外说明。"""


async def generate_script(
    subject: str,
    language: str = "zh-CN",
    paragraph_number: int = 6,
    custom_prompt: str = "",
) -> str:
    """Generate video script using LLM."""
    system_prompt = DEFAULT_SYSTEM_PROMPT
    if custom_prompt:
        system_prompt += f"\n\n额外要求：{custom_prompt}"

    user_prompt = f"请为以下主题撰写{paragraph_number}段短视频旁白文案：\n\n主题：{subject}"

    api_key, base_url, model = _get_llm_config()

    if not api_key:
        logger.warning("No LLM API key configured, returning placeholder script")
        return f"[请配置 LLM API Key 以生成文案]\n\n主题：{subject}\n\n这里将由 AI 生成{paragraph_number}段精彩的短视频旁白文案。"

    try:
        return await call_llm([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ])
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        raise


async def generate_terms(subject: str, script: str) -> list[str]:
    """Generate English search terms for stock video lookup."""
    prompt = f"""Generate 5 English search terms for stock video footage related to this video.

Subject: {subject}
Script excerpt: {script[:500]}

Return ONLY a JSON array of strings, e.g. ["term1", "term2", "term3"]."""

    api_key, _, _ = _get_llm_config()

    if not api_key:
        # Return reasonable defaults based on subject
        return ["nature", "city", "people", "technology", "abstract"]

    try:
        text = await call_llm(
            [
                {"role": "system", "content": "You are a helpful assistant. Respond with only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            max_tokens=256,
        )
        # Extract JSON array
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return ["nature", "city", "people"]
    except Exception as e:
        logger.error(f"Terms generation failed: {e}")
        return ["nature", "city", "people"]
