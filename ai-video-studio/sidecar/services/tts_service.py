"""
TTS service - synthesizes speech from text.
Supports Edge TTS (free), OpenAI TTS, Azure TTS, and Fish Audio.
"""
import os
import asyncio
from pathlib import Path
from loguru import logger


async def synthesize(
    text: str,
    provider: str = "edge-tts",
    voice_name: str = "zh-CN-YunxiNeural",
    voice_rate: float = 1.0,
    voice_volume: float = 1.0,
    output_path: str = "",
    api_key: str = "",
    base_url: str = "",
    model: str = "",
    region: str = "",
) -> str:
    """Synthesize speech using the specified TTS provider."""
    if not output_path:
        output_path = str(Path("./temp") / "audio.mp3")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    if provider == "edge-tts":
        return await _edge_tts(text, voice_name, voice_rate, output_path)
    elif provider == "openai":
        return await _openai_tts(text, voice_name, api_key, base_url, model, output_path)
    elif provider == "azure":
        return await _azure_tts(text, voice_name, api_key, region, output_path)
    elif provider == "fish-audio":
        return await _fish_audio_tts(text, voice_name, api_key, base_url, model, output_path)
    else:
        raise ValueError(f"Unsupported TTS provider: {provider}")


async def _edge_tts(
    text: str,
    voice_name: str,
    voice_rate: float,
    output_path: str,
) -> str:
    """Synthesize using Edge TTS (free)."""
    try:
        import edge_tts
        rate_str = f"+{int((voice_rate - 1) * 100)}%" if voice_rate >= 1 else f"{int((voice_rate - 1) * 100)}%"
        communicate = edge_tts.Communicate(text, voice_name, rate=rate_str)
        await communicate.save(output_path)
        logger.info(f"Edge TTS generated: {output_path}")
        return output_path
    except ImportError:
        logger.error("edge-tts not installed. Run: pip install edge-tts")
        raise
    except Exception as e:
        logger.error(f"Edge TTS failed: {e}")
        raise


async def _openai_tts(
    text: str,
    voice: str,
    api_key: str,
    base_url: str,
    model: str,
    output_path: str,
) -> str:
    """Synthesize using OpenAI TTS API."""
    import httpx

    if not api_key:
        raise ValueError("OpenAI TTS requires an API key")

    url = f"{base_url.rstrip('/')}/audio/speech"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model or "tts-1",
        "input": text,
        "voice": voice or "alloy",
    }

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code != 200:
            raise Exception(f"OpenAI TTS error ({resp.status_code}): {resp.text}")
        with open(output_path, "wb") as f:
            f.write(resp.content)

    logger.info(f"OpenAI TTS generated: {output_path}")
    return output_path


async def _azure_tts(
    text: str,
    voice: str,
    api_key: str,
    region: str,
    output_path: str,
) -> str:
    """Synthesize using Azure Cognitive Services TTS."""
    import httpx

    if not api_key:
        raise ValueError("Azure TTS requires an API key")

    url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
    headers = {
        "Ocp-Apim-Subscription-Key": api_key,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3",
    }
    ssml = f"""<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='zh-CN'>
  <voice name='{voice}'>{text}</voice>
</speak>"""

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url, content=ssml, headers=headers)
        if resp.status_code != 200:
            raise Exception(f"Azure TTS error ({resp.status_code}): {resp.text}")
        with open(output_path, "wb") as f:
            f.write(resp.content)

    logger.info(f"Azure TTS generated: {output_path}")
    return output_path


async def _fish_audio_tts(
    text: str,
    voice: str,
    api_key: str,
    base_url: str,
    model: str,
    output_path: str,
) -> str:
    """Synthesize using Fish Audio TTS API."""
    import httpx

    if not api_key:
        raise ValueError("Fish Audio TTS requires an API key")

    url = f"{base_url.rstrip('/')}/tts"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: dict = {"text": text}
    if voice:
        payload["reference_id"] = voice
    if model:
        payload["model"] = model

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code != 200:
            raise Exception(f"Fish Audio TTS error ({resp.status_code}): {resp.text}")
        with open(output_path, "wb") as f:
            f.write(resp.content)

    logger.info(f"Fish Audio TTS generated: {output_path}")
    return output_path
