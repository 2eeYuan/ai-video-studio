from __future__ import annotations

import json
import logging
from pathlib import Path

from mymovie.agents.base import BaseAgent
from mymovie.bus.message import Message, MessageType
from mymovie.bus.bus import MessageBus
from mymovie.models.story import StoryBrief
from mymovie.utils.llm import LLMClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = Path(__file__).parent.parent.joinpath("prompts/dialog_system.txt").read_text(encoding="utf-8")


class DialogAgent(BaseAgent):
    name = "dialog"

    def __init__(self, bus: MessageBus, llm: LLMClient, topic: str):
        self.bus = bus
        self.llm = llm
        self.topic = topic
        self.messages: list[dict] = []  # conversation history

    def subscribed_types(self) -> list[MessageType]:
        return [MessageType.PIPELINE_START, MessageType.DIALOG_TURN]

    async def handle(self, msg: Message) -> list[Message]:
        if msg.type == MessageType.PIPELINE_START:
            return await self._start_dialog(msg)
        elif msg.type == MessageType.DIALOG_TURN:
            return await self._continue_dialog(msg)
        return []

    async def _start_dialog(self, msg: Message) -> list[Message]:
        # First turn: ask the LLM to start the conversation about the topic
        user_msg = f"用户想要制作一个关于「{self.topic}」的视频。请开始和用户对话，了解故事的详细信息。先问最关键的问题。"
        self.messages.append({"role": "user", "content": user_msg})

        response = await self.llm.chat_messages(SYSTEM_PROMPT, self.messages)
        self.messages.append({"role": "assistant", "content": response})

        # Output the question to the user
        print(f"\n🎬 策划导演: {response}\n")
        return [Message(
            type=MessageType.DIALOG_TURN,
            payload={"question": response},
            sender=self.name,
            correlation_id=msg.correlation_id,
        )]

    async def _continue_dialog(self, msg: Message) -> list[Message]:
        # Get user input
        user_input = input("你: ").strip()

        if user_input.lower() in ("/done", "/完成", "/结束"):
            # Force finalize
            return await self._finalize(msg)

        self.messages.append({"role": "user", "content": user_input})

        # Ask LLM if we have enough info or need more
        check_prompt = user_input + "\n\n---\n请判断：你现在是否有足够信息来生成完整的故事概要？如果信息已经足够，回复「READY_TO_FINALIZE」并附上简要总结。如果还需要更多信息，继续提问。"
        self.messages[-1]["content"] = check_prompt

        response = await self.llm.chat_messages(SYSTEM_PROMPT, self.messages)
        self.messages.append({"role": "assistant", "content": response})

        if "READY_TO_FINALIZE" in response:
            return await self._finalize(msg)

        print(f"\n🎬 策划导演: {response}\n")
        return [Message(
            type=MessageType.DIALOG_TURN,
            payload={"question": response},
            sender=self.name,
            correlation_id=msg.correlation_id,
        )]

    async def _finalize(self, msg: Message) -> list[Message]:
        # Ask LLM to generate structured StoryBrief
        finalize_prompt = "现在请根据我们所有的对话，生成结构化的故事概要JSON。格式：\n" + json.dumps({
            "topic": "主题",
            "genre": "类型",
            "setting": "时代和地点",
            "characters": [{"name": "名字", "role": "角色定位", "appearance": "外貌", "key_traits": "性格特点"}],
            "tone": "基调",
            "target_duration_seconds": 60,
            "visual_style": "视觉风格",
            "additional_notes": "其他备注"
        }, ensure_ascii=False, indent=2)

        self.messages.append({"role": "user", "content": finalize_prompt})
        brief_dict = await self.llm.chat_json(SYSTEM_PROMPT, "\n".join(
            f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}" for m in self.messages
        ))

        story_brief = StoryBrief.from_dict(brief_dict)
        story_brief.topic = self.topic  # ensure topic is set

        print(f"\n✅ 故事概要已确定！\n{story_brief.to_json()}\n")

        return [Message(
            type=MessageType.STORY_DETAILS_READY,
            payload={"story_brief": story_brief},
            sender=self.name,
            correlation_id=msg.correlation_id,
        )]
