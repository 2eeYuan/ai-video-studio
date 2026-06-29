from __future__ import annotations

import logging

from mymovie.agents.base import BaseAgent
from mymovie.bus.message import Message, MessageType
from mymovie.bus.bus import MessageBus

logger = logging.getLogger(__name__)


class ReviewAgent(BaseAgent):
    name = "review"

    def __init__(self, bus: MessageBus):
        self.bus = bus

    def subscribed_types(self) -> list[MessageType]:
        return [MessageType.REVIEW_REQUEST]

    async def handle(self, msg: Message) -> list[Message]:
        video_path = msg.payload.get("video_path", "")

        print(f"\n{'='*60}")
        print(f"🎥 视频已生成！")
        print(f"📁 文件位置: {video_path}")
        print(f"{'='*60}")
        print(f"\n请查看视频后告诉我你的想法。")
        print(f"  - 输入反馈意见来修改视频")
        print(f"  - 输入 'ok' 或 '满意' 来确认完成")
        print(f"  - 输入 '/done' 来强制结束\n")

        feedback = input("你的反馈: ").strip()

        if feedback.lower() in ("ok", "满意", "done", "/done", "完成"):
            print("\n🎉 太好了！视频制作完成！\n")
            return [Message(
                type=MessageType.PIPELINE_COMPLETE,
                payload={"video_path": video_path},
                sender=self.name,
                correlation_id=msg.correlation_id,
            )]
        else:
            print(f"\n📝 收到反馈，正在分析修改意见...\n")
            return [Message(
                type=MessageType.REVISION_REQUEST,
                payload={"feedback": feedback},
                sender=self.name,
                correlation_id=msg.correlation_id,
            )]
