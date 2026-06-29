"""
Kling (可灵) AIGC adapter.
Uses Kling's REST API for text-to-video generation.
"""
import asyncio
import aiohttp
from pathlib import Path
from loguru import logger
from .base import AIGCAdapter, TaskHandle, TaskResult


class KlingAdapter(AIGCAdapter):
    name = "kling"

    def __init__(self, api_key: str = "", base_url: str = "https://api.klingai.com", download_dir: str = "./downloads"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

    async def text2video(self, prompt: str, duration: int = 5, ratio: str = "9:16") -> TaskHandle:
        url = f"{self.base_url}/v1/videos/text2video"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        body = {"prompt": prompt, "duration": duration, "aspect_ratio": ratio}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=body, headers=headers) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise Exception(f"Kling API error ({resp.status}): {text}")
                data = await resp.json()
                task_id = data.get("data", {}).get("task_id", "unknown")
                return TaskHandle(submit_id=task_id, adapter_name=self.name, metadata=data)

    async def query_result(self, handle: TaskHandle) -> TaskResult:
        url = f"{self.base_url}/v1/videos/text2video/{handle.submit_id}"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    return TaskResult(status="failed", error=f"HTTP {resp.status}")
                data = await resp.json()
                task_data = data.get("data", {})
                status = task_data.get("task_status", "processing")

                if status == "succeed":
                    video_url = task_data.get("task_result", {}).get("videos", [{}])[0].get("url", "")
                    return TaskResult(status="success", file_path=video_url, raw_response=data)
                elif status == "failed":
                    return TaskResult(status="failed", error=task_data.get("task_status_msg", "Unknown error"), raw_response=data)
                else:
                    return TaskResult(status="processing", raw_response=data)

    async def download(self, handle: TaskHandle, dest_dir: str) -> str:
        result = await self.query_result(handle)
        if result.file_path:
            return await self._download_file(result.file_path, dest_dir)
        raise Exception("No file available for download")

    async def _download_file(self, url: str, dest_dir: str) -> str:
        import hashlib
        url_hash = hashlib.md5(url.encode()).hexdigest()
        local_path = Path(dest_dir) / f"kling-{url_hash}.mp4"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    raise Exception(f"Download failed: {resp.status}")
                with open(local_path, "wb") as f:
                    async for chunk in resp.content.iter_chunked(8192):
                        f.write(chunk)
        return str(local_path)
