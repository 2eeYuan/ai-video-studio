"""
Director Agent - generates creative direction options for the user.
"""
from pathlib import Path
from loguru import logger
from services.agents.base import BaseAgent

PROMPT_FILE = Path(__file__).parent.parent.parent / "prompts" / "director.txt"


class DirectorAgent(BaseAgent):
    name = "director"

    def __init__(self):
        if PROMPT_FILE.exists():
            self.system_prompt = PROMPT_FILE.read_text(encoding="utf-8").strip()

    async def execute(self, input_data: dict) -> dict:
        """Generate 4 creative directions for the given subject.

        Input: { subject: str }
        Output: { directions: [{ id, label, concept, description }] }
        """
        subject = input_data["subject"]
        logger.info(f"Director Agent: generating directions for '{subject}'")

        result = await self.call_llm(
            user_prompt=f"请为以下主题构思 4 个不同方向的短视频创意：\n\n主题：{subject}",
            temperature=0.8,
        )

        # Validate structure
        directions = result.get("directions", [])
        if len(directions) < 2:
            raise ValueError(f"Director returned too few directions: {len(directions)}")

        # Ensure IDs are set
        for i, d in enumerate(directions):
            d.setdefault("id", i + 1)
            d.setdefault("label", f"方向{i + 1}")
            d.setdefault("concept", "")
            d.setdefault("description", "")

        logger.info(f"Director Agent: generated {len(directions)} directions")
        return {"directions": directions}
