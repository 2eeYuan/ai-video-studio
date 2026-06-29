"""
Storyboard Designer Agent - generates standardized shot tables from scripts.
"""
from pathlib import Path
from loguru import logger
from services.agents.base import BaseAgent

PROMPT_FILE = Path(__file__).parent.parent.parent / "prompts" / "storyboard.txt"


class StoryboardDesignerAgent(BaseAgent):
    name = "storyboard"

    def __init__(self):
        if PROMPT_FILE.exists():
            self.system_prompt = PROMPT_FILE.read_text(encoding="utf-8").strip()

    async def execute(self, input_data: dict) -> dict:
        """Generate a storyboard (shot table) from the script.

        Input: { subject: str, script: { title, characters, scenes } }
        Output: { shots: [{ shot_id, shot_type, angle, description, sound, camera_movement, duration, narration_segment }] }
        """
        subject = input_data["subject"]
        script = input_data["script"]
        logger.info(f"Storyboard Agent: designing shots for '{script.get('title', subject)}'")

        # Build context from script
        characters_str = "\n".join(
            f"- {c['name']}：{c['identity']}，{c['traits']}"
            for c in script.get("characters", [])
        )
        scenes_str = ""
        for s in script.get("scenes", []):
            scenes_str += f"\n场景{s['scene_number']}：{s['location']}，{s['time']}，{'内景' if s.get('interior') else '外景'}\n"
            scenes_str += f"  动作：{s.get('actions', '')}\n"
            scenes_str += f"  旁白：{s.get('narration', '')}\n"
            for d in s.get("dialogue", []):
                scenes_str += f"  {d['character']}：{d['line']}\n"

        user_prompt = f"""请将以下剧本切分为标准化分镜表。

主题：{subject}

角色清单：
{characters_str}

场景列表：
{scenes_str}

请输出完整的分镜表 JSON，每个镜头 2-5 秒。"""

        result = await self.call_llm(user_prompt=user_prompt, temperature=0.6)

        # Validate structure
        shots = result.get("shots", [])
        if not shots:
            raise ValueError("Storyboard returned no shots")

        for shot in shots:
            shot.setdefault("shot_id", "0-0")
            shot.setdefault("shot_type", "中景")
            shot.setdefault("angle", "平视")
            shot.setdefault("description", "")
            shot.setdefault("sound", "")
            shot.setdefault("camera_movement", "固定")
            shot.setdefault("duration", 3)
            shot.setdefault("narration_segment", "")

        total_duration = sum(s.get("duration", 3) for s in shots)
        logger.info(f"Storyboard Agent: generated {len(shots)} shots, total {total_duration}s")
        return {"shots": shots, "total_duration": total_duration}
