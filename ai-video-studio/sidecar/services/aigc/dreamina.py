"""
Dreamina (即梦) AIGC adapter.
Uses the dreamina CLI for text-to-video generation.
"""
import asyncio
import json
import re
from pathlib import Path
from loguru import logger
from .base import AIGCAdapter, TaskHandle, TaskResult


class DreaminaAdapter(AIGCAdapter):
    name = "dreamina"

    def __init__(self, download_dir: str = "./downloads"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

    async def _run_cli(self, cmd: list[str]) -> str:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise Exception(f"dreamina CLI failed: {stderr.decode()}")
        return stdout.decode()

    def _parse_submit_id(self, output: str) -> str:
        try:
            data = json.loads(output)
            return data.get("submit_id") or data.get("id", "unknown")
        except json.JSONDecodeError:
            match = re.search(r'submit_id["\s:]+([a-zA-Z0-9_-]+)', output)
            return match.group(1) if match else "unknown"

    async def text2video(self, prompt: str, duration: int = 5, ratio: str = "9:16") -> TaskHandle:
        cmd = [
            "dreamina", "text2video",
            f"--prompt={prompt}",
            f"--duration={duration}",
            f"--ratio={ratio}",
            "--poll=60",
        ]
        output = await self._run_cli(cmd)
        submit_id = self._parse_submit_id(output)
        return TaskHandle(
            submit_id=submit_id,
            adapter_name=self.name,
            metadata={"output": output, "duration": duration},
        )

    async def query_result(self, handle: TaskHandle) -> TaskResult:
        try:
            output = await self._run_cli([
                "dreamina", "query_result",
                f"--submit_id={handle.submit_id}",
                f"--download_dir={str(self.download_dir)}",
            ])
            data = json.loads(output)
            return TaskResult(
                status=data.get("status", "processing"),
                file_path=data.get("file_path"),
                raw_response=data,
            )
        except Exception as e:
            return TaskResult(status="failed", error=str(e))

    async def download(self, handle: TaskHandle, dest_dir: str) -> str:
        result = await self.query_result(handle)
        if result.file_path:
            return result.file_path
        raise Exception("No file available for download")
