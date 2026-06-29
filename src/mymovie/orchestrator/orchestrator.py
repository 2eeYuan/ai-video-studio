from __future__ import annotations

import asyncio
import logging

from mymovie.bus.message import Message, MessageType
from mymovie.bus.bus import MessageBus
from mymovie.models.pipeline import PipelineContext, PipelineState

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self, bus: MessageBus, context: PipelineContext):
        self.bus = bus
        self.context = context
        self.state = context.state
        self._queue: asyncio.Queue | None = None

    def _subscribed_types(self) -> list[MessageType]:
        return [
            MessageType.STORY_DETAILS_READY,
            MessageType.RESEARCH_COMPLETE,
            MessageType.SCRIPT_READY,
            MessageType.STORYBOARD_READY,
            MessageType.PROMPTS_READY,
            MessageType.SEGMENTS_READY,
            MessageType.VIDEOGEN_SEGMENT_DONE,
            MessageType.VIDEOGEN_ALL_DONE,
            MessageType.ASSEMBLY_DONE,
            MessageType.PIPELINE_COMPLETE,
            MessageType.REVISION_SEGMENTS_READY,
            MessageType.AGENT_ERROR,
        ]

    async def start(self):
        self._queue = self.bus.register("orchestrator", self._subscribed_types())
        logger.info("Orchestrator started")
        try:
            while self.state != PipelineState.DONE:
                msg = await self._queue.get()
                await self._transition(msg)
        except asyncio.CancelledError:
            logger.info("Orchestrator stopped")

    async def _transition(self, msg: Message):
        logger.info(f"Orchestrator: state={self.state.value}, msg={msg.type.value}")

        match (self.state, msg.type):

            # --- Initial: kick off dialog ---
            case (PipelineState.IDLE, MessageType.STORY_DETAILS_READY):
                # This shouldn't happen in IDLE, but handle gracefully
                pass

            # --- Dialog complete -> start research ---
            case (PipelineState.DIALOG, MessageType.STORY_DETAILS_READY):
                self.context.story_brief = msg.payload.get("story_brief")
                self.context.state = PipelineState.RESEARCH
                self.context.save()
                await self.bus.publish(Message(
                    type=MessageType.RESEARCH_REQUEST,
                    payload={"story_brief": self.context.story_brief},
                    sender="orchestrator",
                    correlation_id=self.context.correlation_id,
                ))

            # --- Research complete -> start scriptwriting ---
            case (PipelineState.RESEARCH, MessageType.RESEARCH_COMPLETE):
                self.context.research_pack = msg.payload.get("research_pack")
                self.context.state = PipelineState.SCRIPT
                self.context.save()
                await self.bus.publish(Message(
                    type=MessageType.SCRIPT_REQUEST,
                    payload={
                        "story_brief": self.context.story_brief,
                        "research_pack": self.context.research_pack,
                    },
                    sender="orchestrator",
                    correlation_id=self.context.correlation_id,
                ))

            # --- Script complete -> start storyboard ---
            case (PipelineState.SCRIPT, MessageType.SCRIPT_READY):
                self.context.script = msg.payload.get("script")
                self.context.state = PipelineState.STORYBOARD
                self.context.save()
                await self.bus.publish(Message(
                    type=MessageType.STORYBOARD_REQUEST,
                    payload={"script": self.context.script},
                    sender="orchestrator",
                    correlation_id=self.context.correlation_id,
                ))

            # --- Storyboard complete -> start prompt generation ---
            case (PipelineState.STORYBOARD, MessageType.STORYBOARD_READY):
                self.context.storyboard = msg.payload.get("storyboard")
                self.context.state = PipelineState.PROMPT_GENERATION
                self.context.save()
                await self.bus.publish(Message(
                    type=MessageType.PROMPT_REQUEST,
                    payload={"storyboard": self.context.storyboard},
                    sender="orchestrator",
                    correlation_id=self.context.correlation_id,
                ))

            # --- Prompts ready -> start segmentation ---
            case (PipelineState.PROMPT_GENERATION, MessageType.PROMPTS_READY):
                self.context.prompts = msg.payload.get("prompts", [])
                self.context.state = PipelineState.SEGMENTATION
                self.context.save()
                await self.bus.publish(Message(
                    type=MessageType.SEGMENTATION_REQUEST,
                    payload={"prompts": self.context.prompts},
                    sender="orchestrator",
                    correlation_id=self.context.correlation_id,
                ))

            # --- Segments ready -> start video generation ---
            case (PipelineState.SEGMENTATION, MessageType.SEGMENTS_READY):
                self.context.segments = msg.payload.get("segments", [])
                self.context.state = PipelineState.VIDEO_GENERATION
                self.context.save()
                # Send one request per segment
                for seg in self.context.segments:
                    await self.bus.publish(Message(
                        type=MessageType.VIDEOGEN_REQUEST,
                        payload={"segment": seg},
                        sender="orchestrator",
                        correlation_id=self.context.correlation_id,
                    ))

            # --- Individual segment done ---
            case (PipelineState.VIDEO_GENERATION, MessageType.VIDEOGEN_SEGMENT_DONE):
                seg_index = msg.payload.get("segment_index")
                video_path = msg.payload.get("video_path")
                if seg_index is not None:
                    self.context.video_paths[seg_index] = video_path
                    # Update segment status
                    for seg in self.context.segments:
                        if seg.index == seg_index:
                            seg.video_path = video_path
                            seg.status = "done"
                            break
                    self.context.save()

            # --- All segments done -> assembly ---
            case (PipelineState.VIDEO_GENERATION, MessageType.VIDEOGEN_ALL_DONE):
                self.context.state = PipelineState.ASSEMBLY
                self.context.save()
                # Build ordered list of video paths
                ordered_paths = [
                    self.context.video_paths[i]
                    for i in sorted(self.context.video_paths.keys())
                    if self.context.video_paths[i]
                ]
                await self.bus.publish(Message(
                    type=MessageType.ASSEMBLY_REQUEST,
                    payload={"video_paths": ordered_paths},
                    sender="orchestrator",
                    correlation_id=self.context.correlation_id,
                ))

            # --- Assembly done -> review ---
            case (PipelineState.ASSEMBLY, MessageType.ASSEMBLY_DONE):
                self.context.final_video_path = msg.payload.get("output_path")
                self.context.state = PipelineState.REVIEW
                self.context.save()
                await self.bus.publish(Message(
                    type=MessageType.REVIEW_REQUEST,
                    payload={"video_path": self.context.final_video_path},
                    sender="orchestrator",
                    correlation_id=self.context.correlation_id,
                ))

            # --- Review: user wants changes ---
            case (PipelineState.REVIEW, MessageType.REVISION_REQUEST):
                self.context.state = PipelineState.REVISION
                self.context.save()
                await self.bus.publish(Message(
                    type=MessageType.REVISION_REQUEST,
                    payload={
                        "feedback": msg.payload.get("feedback"),
                        "script": self.context.script,
                        "storyboard": self.context.storyboard,
                        "segments": self.context.segments,
                    },
                    sender="orchestrator",
                    correlation_id=self.context.correlation_id,
                ))

            # --- Revision plan ready -> re-generate affected segments ---
            case (PipelineState.REVISION, MessageType.REVISION_SEGMENTS_READY):
                revision_plan = msg.payload.get("revision_plan")
                self.context.revision_count += 1

                # Apply removals
                if revision_plan and hasattr(revision_plan, 'segments_to_remove'):
                    remove_indices = set(revision_plan.segments_to_remove)
                    self.context.segments = [
                        s for s in self.context.segments if s.index not in remove_indices
                    ]

                # Apply additions
                if revision_plan and hasattr(revision_plan, 'segments_to_add'):
                    for addition in revision_plan.segments_to_add:
                        from mymovie.models.segment import Segment
                        new_seg = Segment(
                            index=addition.insert_after + 1,
                            prompt=addition.prompt,
                            duration=addition.duration,
                            status="pending",
                        )
                        self.context.segments.append(new_seg)

                # Apply revisions
                segments_to_regenerate = []
                if revision_plan and hasattr(revision_plan, 'segments_to_regenerate'):
                    for rev in revision_plan.segments_to_regenerate:
                        for seg in self.context.segments:
                            if seg.index == rev.segment_index:
                                seg.prompt = rev.new_prompt
                                seg.status = "pending"
                                segments_to_regenerate.append(seg)
                                break

                # Re-index segments
                self.context.segments.sort(key=lambda s: s.index)
                for i, seg in enumerate(self.context.segments):
                    seg.index = i

                # Clear video paths for segments that need regeneration
                for seg in segments_to_regenerate:
                    self.context.video_paths.pop(seg.index, None)

                self.context.state = PipelineState.VIDEO_GENERATION
                self.context.save()

                # Only send requests for pending segments
                for seg in self.context.segments:
                    if seg.status == "pending":
                        await self.bus.publish(Message(
                            type=MessageType.VIDEOGEN_REQUEST,
                            payload={"segment": seg},
                            sender="orchestrator",
                            correlation_id=self.context.correlation_id,
                        ))

            # --- Review: user is done ---
            case (PipelineState.REVIEW, MessageType.PIPELINE_COMPLETE):
                self.context.state = PipelineState.DONE
                self.context.save()
                logger.info(f"Pipeline complete! Final video: {self.context.final_video_path}")

            # --- Error handling ---
            case (_, MessageType.AGENT_ERROR):
                agent = msg.payload.get("agent", "unknown")
                error = msg.payload.get("error", "unknown error")
                recoverable = msg.payload.get("recoverable", True)
                logger.error(f"Agent error from '{agent}': {error} (recoverable={recoverable})")
                if not recoverable:
                    self.context.state = PipelineState.DONE

            case _:
                logger.warning(f"Unexpected message {msg.type.value} in state {self.state.value}")

    def kick_off(self):
        """Called externally to start the pipeline from IDLE."""
        self.state = PipelineState.DIALOG
        self.context.state = PipelineState.DIALOG
