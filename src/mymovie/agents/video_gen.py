from __future__ import annotations

import asyncio
import logging

from mymovie.agents.base import BaseAgent
from mymovie.adapters.base import AIGCAdapter, AIGCAdapterError
from mymovie.adapters.registry import AdapterRegistry
from mymovie.bus.message import Message, MessageType
from mymovie.bus.bus import MessageBus
from mymovie.models.segment import Segment

logger = logging.getLogger(__name__)


class VideoGenAgent(BaseAgent):
    name = "video_gen"

    def __init__(self, bus: MessageBus, adapter_registry: AdapterRegistry,
                 default_adapter: str = "dreamina", max_retries: int = 3):
        self.bus = bus
        self.adapter_registry = adapter_registry
        self.default_adapter = default_adapter
        self.max_retries = max_retries
        self._completed_count = 0
        self._total_count = 0

    def subscribed_types(self) -> list[MessageType]:
        return [MessageType.VIDEOGEN_REQUEST]

    async def handle(self, msg: Message) -> list[Message]:
        segment: Segment = msg.payload.get("segment")
        if not segment:
            return []

        adapter = self.adapter_registry.get(segment.adapter_name or self.default_adapter)

        logger.info(f"VideoGenAgent: generating segment {segment.index} ({segment.duration}s)...")

        video_path = await self._generate_with_retry(segment, adapter)

        if video_path:
            self._completed_count += 1
            logger.info(f"VideoGenAgent: segment {segment.index} done ({self._completed_count}/{self._total_count})")

            result = [Message(
                type=MessageType.VIDEOGEN_SEGMENT_DONE,
                payload={"segment_index": segment.index, "video_path": video_path},
                sender=self.name,
                correlation_id=msg.correlation_id,
            )]

            # Check if all segments are done (this is a simplification;
            # the orchestrator tracks overall completion)
            return result
        else:
            return [Message(
                type=MessageType.AGENT_ERROR,
                payload={
                    "agent": self.name,
                    "segment_index": segment.index,
                    "error": f"Failed to generate segment {segment.index} after {self.max_retries} attempts",
                    "recoverable": False,
                },
                sender=self.name,
                correlation_id=msg.correlation_id,
            )]

    async def _generate_with_retry(self, segment: Segment, adapter: AIGCAdapter) -> str | None:
        for attempt in range(self.max_retries):
            try:
                segment.status = "generating"
                segment.generation_attempts += 1

                handle = await adapter.text2video(
                    prompt=segment.prompt,
                    duration=segment.duration,
                )
                segment.submit_id = handle.submit_id

                # Poll for result
                result = await adapter.query_result(handle)
                if result.status == "success" and result.file_path:
                    segment.status = "done"
                    segment.video_path = result.file_path
                    return result.file_path

                # If still querying, try download
                file_path = await adapter.download(handle, adapter.download_dir if hasattr(adapter, 'download_dir') else "./downloads")
                if file_path:
                    segment.status = "done"
                    segment.video_path = file_path
                    return file_path

                segment.error_log.append(f"Attempt {attempt + 1}: status={result.status}")

            except AIGCAdapterError as e:
                segment.error_log.append(f"Attempt {attempt + 1}: {e}")
                logger.warning(f"VideoGenAgent: segment {segment.index} attempt {attempt + 1} failed: {e}")

            except Exception as e:
                segment.error_log.append(f"Attempt {attempt + 1}: unexpected error: {e}")
                logger.error(f"VideoGenAgent: segment {segment.index} unexpected error: {e}", exc_info=True)

            if attempt < self.max_retries - 1:
                wait = 5 * (2 ** attempt)
                logger.info(f"VideoGenAgent: retrying segment {segment.index} in {wait}s...")
                await asyncio.sleep(wait)

        segment.status = "failed"
        return None
