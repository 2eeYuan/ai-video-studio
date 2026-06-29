"""
Agent Orchestrator - manages multi-stage pipeline with user confirmation points.
"""
import uuid
from enum import Enum
from typing import Optional
from loguru import logger

from services.agents.director import DirectorAgent
from services.agents.script_writer import ScriptWriterAgent
from services.agents.storyboard import StoryboardDesignerAgent


class AgentStage(str, Enum):
    DIRECTION = "direction"       # Director generates options
    DIRECTION_CHOSEN = "direction_chosen"  # User chose, awaiting script
    SCRIPT = "script"             # Script generated, awaiting confirmation
    STORYBOARD = "storyboard"     # Storyboard generated, awaiting confirmation
    GENERATING = "generating"     # Handing off to video pipeline
    DONE = "done"
    FAILED = "failed"


class AgentSession:
    def __init__(self, task_id: str, subject: str):
        self.task_id = task_id
        self.subject = subject
        self.stage = AgentStage.DIRECTION
        self.directions: Optional[list] = None
        self.chosen_direction: Optional[dict] = None
        self.script: Optional[dict] = None
        self.storyboard: Optional[dict] = None
        self.error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "stage": self.stage.value,
            "subject": self.subject,
            "directions": self.directions,
            "chosen_direction": self.chosen_direction,
            "script": self.script,
            "storyboard": self.storyboard,
            "status": self.stage.value,
            "error": self.error,
        }


class AgentOrchestrator:
    """Manages agent sessions and stage transitions."""

    def __init__(self):
        self.sessions: dict[str, AgentSession] = {}
        self._director = DirectorAgent()
        self._script_writer = ScriptWriterAgent()
        self._storyboard = StoryboardDesignerAgent()

    def get_session(self, task_id: str) -> Optional[AgentSession]:
        return self.sessions.get(task_id)

    async def start(self, task_id: str, subject: str) -> AgentSession:
        """Start a new agent session. Runs Director Agent to generate directions."""
        session = AgentSession(task_id, subject)
        self.sessions[task_id] = session

        try:
            logger.info(f"[{task_id}] Starting agent session for '{subject}'")
            result = await self._director.execute({"subject": subject})
            session.directions = result["directions"]
            session.stage = AgentStage.DIRECTION
            logger.info(f"[{task_id}] Director generated {len(session.directions)} directions")
        except Exception as e:
            session.stage = AgentStage.FAILED
            session.error = str(e)
            logger.error(f"[{task_id}] Director failed: {e}")

        return session

    async def submit_direction(self, task_id: str, direction_id: int) -> AgentSession:
        """User chose a direction. Run ScriptWriter Agent."""
        session = self.sessions.get(task_id)
        if not session:
            raise ValueError(f"Session {task_id} not found")

        # Find the chosen direction
        chosen = None
        for d in (session.directions or []):
            if d.get("id") == direction_id:
                chosen = d
                break
        if not chosen:
            raise ValueError(f"Direction {direction_id} not found")

        session.chosen_direction = chosen
        session.stage = AgentStage.DIRECTION_CHOSEN

        try:
            logger.info(f"[{task_id}] User chose direction: {chosen['label']}")
            result = await self._script_writer.execute({
                "subject": session.subject,
                "direction": chosen,
            })
            session.script = result
            session.stage = AgentStage.SCRIPT
            logger.info(f"[{task_id}] ScriptWriter generated script with {len(result.get('scenes', []))} scenes")
        except Exception as e:
            session.stage = AgentStage.FAILED
            session.error = str(e)
            logger.error(f"[{task_id}] ScriptWriter failed: {e}")

        return session

    async def submit_script(self, task_id: str, script: Optional[dict] = None) -> AgentSession:
        """User confirmed (or edited) the script. Run Storyboard Agent."""
        session = self.sessions.get(task_id)
        if not session:
            raise ValueError(f"Session {task_id} not found")

        # Use edited script if provided
        if script:
            session.script = script

        if not session.script:
            raise ValueError("No script to process")

        try:
            logger.info(f"[{task_id}] Script confirmed, generating storyboard")
            result = await self._storyboard.execute({
                "subject": session.subject,
                "script": session.script,
            })
            session.storyboard = result
            session.stage = AgentStage.STORYBOARD
            logger.info(f"[{task_id}] Storyboard generated {len(result.get('shots', []))} shots")
        except Exception as e:
            session.stage = AgentStage.FAILED
            session.error = str(e)
            logger.error(f"[{task_id}] Storyboard failed: {e}")

        return session

    async def submit_storyboard(self, task_id: str) -> AgentSession:
        """User confirmed the storyboard. Ready for video generation."""
        session = self.sessions.get(task_id)
        if not session:
            raise ValueError(f"Session {task_id} not found")

        session.stage = AgentStage.GENERATING
        logger.info(f"[{task_id}] Storyboard confirmed, ready for video generation")
        return session


# Global singleton
orchestrator = AgentOrchestrator()
