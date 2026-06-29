from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path

from mymovie.adapters.base import AIGCAdapter, AIGCAdapterError, TaskHandle, TaskResult
from mymovie.config import DreaminaConfig

logger = logging.getLogger(__name__)


class DreaminaAdapter(AIGCAdapter):
    name = "dreamina"

    def __init__(self, config: DreaminaConfig):
        self.config = config
        self.download_dir = Path(config.download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

    async def _run_cli(self, cmd: list[str]) -> str:
        logger.debug(f"Running: {' '.join(cmd)}")
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise AIGCAdapterError(f"dreamina CLI failed (rc={proc.returncode}): {stderr.decode()}")
        return stdout.decode()

    def _parse_submit_id(self, output: str) -> str | None:
        """Extract submit_id from CLI output."""
        # Try JSON first
        try:
            data = json.loads(output)
            if isinstance(data, dict):
                return data.get("submit_id") or data.get("id")
        except json.JSONDecodeError:
            pass
        # Try regex
        match = re.search(r'submit_id["\s:]+([a-zA-Z0-9_-]+)', output)
        if match:
            return match.group(1)
        return None

    async def text2video(self, prompt: str, duration: int,
                         ratio: str = "16:9", resolution: str = "720P") -> TaskHandle:
        cmd = [
            "dreamina", "text2video",
            f"--prompt={prompt}",
            f"--duration={duration}",
            f"--ratio={ratio}",
            f"--video_resolution={resolution}",
            f"--poll={self.config.poll_timeout}",
        ]
        output = await self._run_cli(cmd)
        submit_id = self._parse_submit_id(output) or "unknown"
        return TaskHandle(
            submit_id=submit_id,
            adapter_name=self.name,
            metadata={"output": output, "duration": duration, "ratio": ratio},
        )

    async def text2image(self, prompt: str, ratio: str = "1:1",
                         resolution: str = "2k") -> TaskHandle:
        cmd = [
            "dreamina", "text2image",
            f"--prompt={prompt}",
            f"--ratio={ratio}",
            f"--resolution_type={resolution}",
            f"--poll={self.config.poll_timeout}",
        ]
        output = await self._run_cli(cmd)
        submit_id = self._parse_submit_id(output) or "unknown"
        return TaskHandle(
            submit_id=submit_id,
            adapter_name=self.name,
            metadata={"output": output},
        )

    async def image2video(self, image_path: str, prompt: str,
                          duration: int) -> TaskHandle:
        cmd = [
            "dreamina", "image2video",
            f"--image={image_path}",
            f"--prompt={prompt}",
            f"--duration={duration}",
            f"--poll={self.config.poll_timeout}",
        ]
        output = await self._run_cli(cmd)
        submit_id = self._parse_submit_id(output) or "unknown"
        return TaskHandle(
            submit_id=submit_id,
            adapter_name=self.name,
            metadata={"output": output, "image_path": image_path},
        )

    async def query_result(self, handle: TaskHandle) -> TaskResult:
        try:
            output = await self._run_cli([
                "dreamina", "query_result",
                f"--submit_id={handle.submit_id}",
                f"--download_dir={self.download_dir}",
            ])
        except AIGCAdapterError as e:
            return TaskResult(status="failed", error=str(e))

        try:
            data = json.loads(output)
            status = data.get("status", "querying")
            file_path = data.get("file_path") or data.get("url")
            return TaskResult(status=status, file_path=file_path, raw_response=data)
        except json.JSONDecodeError:
            # Check if it indicates success in plain text
            if "success" in output.lower() or "done" in output.lower():
                return TaskResult(status="success", raw_response={"output": output})
            return TaskResult(status="querying", raw_response={"output": output})

    async def download(self, handle: TaskHandle, dest_dir: str) -> str:
        result = await self.query_result(handle)
        if result.file_path:
            # If the result already has a local file path
            return result.file_path
        # Try downloading via CLI
        output = await self._run_cli([
            "dreamina", "query_result",
            f"--submit_id={handle.submit_id}",
            f"--download_dir={dest_dir}",
        ])
        try:
            data = json.loads(output)
            return data.get("file_path", "")
        except json.JSONDecodeError:
            return ""

    def supported_durations(self) -> list[int]:
        return [5, 10]

    def max_prompt_length(self) -> int:
        return 2000
