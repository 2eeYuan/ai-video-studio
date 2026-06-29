"""
Script Writer Agent - generates structured video scripts.
"""
from pathlib import Path
from loguru import logger
from services.agents.base import BaseAgent

PROMPT_FILE = Path(__file__).parent.parent.parent / "prompts" / "script_writer.txt"


class ScriptWriterAgent(BaseAgent):
    name = "script_writer"

    def __init__(self):
        if PROMPT_FILE.exists():
            self.system_prompt = PROMPT_FILE.read_text(encoding="utf-8").strip()

    async def execute(self, input_data: dict) -> dict:
        """Generate a structured script based on the chosen direction.

        Input: { subject: str, direction: { label, concept, description } }
        Output: { title, characters: [...], scenes: [...] }
        """
        subject = input_data["subject"]
        direction = input_data["direction"]
        logger.info(f"ScriptWriter Agent: writing script for '{subject}' ({direction['label']})")

        user_prompt = f"""请根据以下创意方向，创作完整的短视频剧本。

主题：{subject}
风格：{direction['label']}
核心概念：{direction['concept']}
场景描述：{direction['description']}

请输出完整的结构化剧本 JSON。"""

        result = await self.call_llm(user_prompt=user_prompt, temperature=0.7)

        # Validate structure
        if "scenes" not in result:
            raise ValueError("Script missing 'scenes' field")

        result.setdefault("title", subject)
        result.setdefault("characters", [])

        for scene in result["scenes"]:
            scene.setdefault("scene_number", 0)
            scene.setdefault("location", "")
            scene.setdefault("time", "")
            scene.setdefault("interior", True)
            scene.setdefault("actions", "")
            scene.setdefault("narration", "")
            scene.setdefault("dialogue", [])

        # Generate combined narration text from scenes
        narrations = [s.get("narration", "") for s in result["scenes"] if s.get("narration")]
        result["full_narration"] = "\n".join(narrations)

        logger.info(f"ScriptWriter Agent: generated {len(result['scenes'])} scenes")
        return result
