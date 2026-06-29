from __future__ import annotations

import argparse
import asyncio
import logging
import uuid
from pathlib import Path

from rich.console import Console

from mymovie.adapters.dreamina import DreaminaAdapter
from mymovie.adapters.registry import AdapterRegistry
from mymovie.agents.assembly import AssemblyAgent
from mymovie.agents.dialog import DialogAgent
from mymovie.agents.prompt_gen import PromptAgent
from mymovie.agents.research import ResearchAgent
from mymovie.agents.review import ReviewAgent
from mymovie.agents.revision import RevisionAgent
from mymovie.agents.scriptwriter import ScriptwriterAgent
from mymovie.agents.segmentation import SegmentationAgent
from mymovie.agents.storyboard import StoryboardAgent
from mymovie.agents.video_gen import VideoGenAgent
from mymovie.bus.bus import MessageBus
from mymovie.bus.message import Message, MessageType
from mymovie.config import load_config
from mymovie.models.pipeline import PipelineContext, PipelineState
from mymovie.orchestrator.orchestrator import Orchestrator
from mymovie.utils.llm import LLMClient
from mymovie.utils.logger import setup_logging

logger = logging.getLogger(__name__)
console = Console()


async def run_pipeline(args):
    """Run the full video production pipeline."""
    config = load_config()
    llm = LLMClient(config.llm)

    # Create project directory
    project_name = args.topic.replace(" ", "_")[:50]
    project_dir = Path(config.projects.base_dir) / project_name
    project_dir.mkdir(parents=True, exist_ok=True)

    # Initialize pipeline context
    correlation_id = uuid.uuid4().hex[:12]
    context = PipelineContext(
        correlation_id=correlation_id,
        project_dir=project_dir,
    )

    # Set up message bus
    bus = MessageBus()

    # Set up AIGC adapter registry
    adapter_registry = AdapterRegistry()
    adapter_registry.register(DreaminaAdapter(config.adapters.dreamina))

    # Create agents
    dialog_agent = DialogAgent(bus, llm, args.topic)
    research_agent = ResearchAgent(bus, llm)
    scriptwriter_agent = ScriptwriterAgent(bus, llm)
    storyboard_agent = StoryboardAgent(bus, llm)
    prompt_agent = PromptAgent(bus, llm)
    segmentation_agent = SegmentationAgent(bus, max_duration=max(config.video.segment_durations))
    video_gen_agent = VideoGenAgent(
        bus, adapter_registry,
        default_adapter=config.adapters.default,
        max_retries=config.adapters.dreamina.max_retries,
    )
    assembly_agent = AssemblyAgent(bus, config.video.ffmpeg, project_dir)
    review_agent = ReviewAgent(bus)
    revision_agent = RevisionAgent(bus, llm)

    # Create orchestrator
    orchestrator = Orchestrator(bus, context)

    console.print(f"\n[bold green]🎬 AI视频生产流水线启动[/bold green]")
    console.print(f"[dim]主题: {args.topic}[/dim]")
    console.print(f"[dim]项目目录: {project_dir}[/dim]")
    console.print(f"[dim]AIGC工具: {config.adapters.default}[/dim]\n")

    # Start all agents as concurrent tasks
    tasks = [
        asyncio.create_task(orchestrator.start(), name="orchestrator"),
        asyncio.create_task(dialog_agent.start(), name="dialog"),
        asyncio.create_task(research_agent.start(), name="research"),
        asyncio.create_task(scriptwriter_agent.start(), name="scriptwriter"),
        asyncio.create_task(storyboard_agent.start(), name="storyboard"),
        asyncio.create_task(prompt_agent.start(), name="prompt_gen"),
        asyncio.create_task(segmentation_agent.start(), name="segmentation"),
        asyncio.create_task(video_gen_agent.start(), name="video_gen"),
        asyncio.create_task(assembly_agent.start(), name="assembly"),
        asyncio.create_task(review_agent.start(), name="review"),
        asyncio.create_task(revision_agent.start(), name="revision"),
    ]

    # Kick off the pipeline by telling the orchestrator to start dialog
    orchestrator.kick_off()
    await bus.publish(Message(
        type=MessageType.PIPELINE_START,
        payload={"topic": args.topic},
        sender="main",
        correlation_id=correlation_id,
    ))

    try:
        # Wait for orchestrator to reach DONE state
        await tasks[0]  # orchestrator task
    except asyncio.CancelledError:
        pass
    except KeyboardInterrupt:
        console.print("\n[yellow]用户中断，正在保存状态...[/yellow]")
        context.save()
    finally:
        # Cancel all agent tasks
        for t in tasks:
            if not t.done():
                t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    console.print(f"\n[bold]项目产物保存在: {project_dir}[/bold]")


async def resume_pipeline(project_dir: str):
    """Resume a pipeline from checkpoint."""
    config = load_config()
    llm = LLMClient(config.llm)

    path = Path(project_dir)
    if not (path / "pipeline_state.json").exists():
        console.print(f"[red]错误: 在 {project_dir} 中找不到 pipeline_state.json[/red]")
        return

    context = PipelineContext.load(path)
    console.print(f"\n[bold green]🔄 恢复流水线[/bold green]")
    console.print(f"[dim]状态: {context.state.value}[/dim]")
    console.print(f"[dim]项目目录: {path}[/dim]\n")

    # Set up message bus and agents (same as run_pipeline)
    bus = MessageBus()
    adapter_registry = AdapterRegistry()
    adapter_registry.register(DreaminaAdapter(config.adapters.dreamina))

    dialog_agent = DialogAgent(bus, llm, context.story_brief.topic if context.story_brief else "恢复项目")
    research_agent = ResearchAgent(bus, llm)
    scriptwriter_agent = ScriptwriterAgent(bus, llm)
    storyboard_agent = StoryboardAgent(bus, llm)
    prompt_agent = PromptAgent(bus, llm)
    segmentation_agent = SegmentationAgent(bus, max_duration=max(config.video.segment_durations))
    video_gen_agent = VideoGenAgent(
        bus, adapter_registry,
        default_adapter=config.adapters.default,
        max_retries=config.adapters.dreamina.max_retries,
    )
    assembly_agent = AssemblyAgent(bus, config.video.ffmpeg, path)
    review_agent = ReviewAgent(bus)
    revision_agent = RevisionAgent(bus, llm)

    orchestrator = Orchestrator(bus, context)

    tasks = [
        asyncio.create_task(orchestrator.start(), name="orchestrator"),
        asyncio.create_task(dialog_agent.start(), name="dialog"),
        asyncio.create_task(research_agent.start(), name="research"),
        asyncio.create_task(scriptwriter_agent.start(), name="scriptwriter"),
        asyncio.create_task(storyboard_agent.start(), name="storyboard"),
        asyncio.create_task(prompt_agent.start(), name="prompt_gen"),
        asyncio.create_task(segmentation_agent.start(), name="segmentation"),
        asyncio.create_task(video_gen_agent.start(), name="video_gen"),
        asyncio.create_task(assembly_agent.start(), name="assembly"),
        asyncio.create_task(review_agent.start(), name="review"),
        asyncio.create_task(revision_agent.start(), name="revision"),
    ]

    # Publish the appropriate message based on where we left off
    if context.state == PipelineState.DIALOG:
        await bus.publish(Message(
            type=MessageType.DIALOG_TURN,
            payload={},
            sender="main",
            correlation_id=context.correlation_id,
        ))
    # For other states, the orchestrator will handle based on its current state

    try:
        await tasks[0]
    except asyncio.CancelledError:
        pass
    except KeyboardInterrupt:
        console.print("\n[yellow]用户中断，正在保存状态...[/yellow]")
        context.save()
    finally:
        for t in tasks:
            if not t.done():
                t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


def main():
    setup_logging()

    parser = argparse.ArgumentParser(description="AI全自动视频生产流水线")
    sub = parser.add_subparsers(dest="command")

    # new command
    new_parser = sub.add_parser("new", help="新建视频项目")
    new_parser.add_argument("topic", help="视频主题")
    new_parser.add_argument("--adapter", default="dreamina", help="AIGC工具 (default: dreamina)")
    new_parser.add_argument("--style", default="cinematic", help="视觉风格 (default: cinematic)")
    new_parser.add_argument("--duration", type=int, default=60, help="目标时长秒数 (default: 60)")

    # resume command
    resume_parser = sub.add_parser("resume", help="从检查点恢复项目")
    resume_parser.add_argument("project_dir", help="项目目录路径")

    args = parser.parse_args()

    if args.command == "new":
        asyncio.run(run_pipeline(args))
    elif args.command == "resume":
        asyncio.run(resume_pipeline(args.project_dir))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
