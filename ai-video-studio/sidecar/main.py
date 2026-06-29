"""
AI Video Studio - Python Sidecar
FastAPI server for video generation pipeline.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
from loguru import logger
import asyncio

app = FastAPI(title="AI Video Studio Sidecar", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
async def load_config_on_startup():
    """Load config.yaml into LLM runtime config on startup."""
    import yaml
    config_path = Path(__file__).parent / "config.yaml"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            from services.llm_service import update_config
            update_config(cfg)
            logger.info(f"Loaded config.yaml: LLM provider={cfg.get('llm', {}).get('provider', '?')}")
        except Exception as e:
            logger.warning(f"Failed to load config.yaml: {e}")


class ScriptRequest(BaseModel):
    subject: str
    language: str = "zh-CN"
    paragraph_number: int = 6
    custom_prompt: str = ""


class TermsRequest(BaseModel):
    subject: str
    script: str


class TTSRequest(BaseModel):
    text: str
    provider: str = "edge-tts"
    voice_name: str = "zh-CN-YunxiNeural"
    voice_rate: float = 1.0
    voice_volume: float = 1.0
    output_path: str = ""
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    region: str = ""


class PipelineRequest(BaseModel):
    task_id: str
    subject: str
    script: str = ""
    keywords: str = ""
    shots: Optional[List[dict]] = None
    mode: str = "aigc"
    aspect: str = "9:16"
    clip_duration: int = 3
    subtitle_config: Optional[dict] = None
    bgm_config: Optional[dict] = None


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


@app.post("/generate/script")
async def generate_script_endpoint(req: ScriptRequest):
    """Generate video script using LLM."""
    from services.llm_service import generate_script, generate_terms
    try:
        script = await generate_script(
            subject=req.subject,
            language=req.language,
            paragraph_number=req.paragraph_number,
            custom_prompt=req.custom_prompt,
        )
        terms = await generate_terms(subject=req.subject, script=script)
        return {"script": script, "keywords": terms}
    except Exception as e:
        logger.error(f"Script generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate/terms")
async def generate_terms_endpoint(req: TermsRequest):
    """Generate search terms from script."""
    from services.llm_service import generate_terms
    try:
        terms = await generate_terms(subject=req.subject, script=req.script)
        return {"keywords": terms}
    except Exception as e:
        logger.error(f"Terms generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate/audio")
async def generate_audio_endpoint(req: TTSRequest):
    """Generate audio using TTS."""
    from services.tts_service import synthesize
    try:
        path = await synthesize(
            text=req.text,
            provider=req.provider,
            voice_name=req.voice_name,
            voice_rate=req.voice_rate,
            voice_volume=req.voice_volume,
            output_path=req.output_path,
            api_key=req.api_key,
            base_url=req.base_url,
            model=req.model,
            region=req.region,
        )
        return {"audio_path": path}
    except Exception as e:
        logger.error(f"Audio generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pipeline/start")
async def start_pipeline(req: PipelineRequest):
    """Start the full video generation pipeline."""
    from services.pipeline_service import run_pipeline
    # Run pipeline in background
    asyncio.create_task(run_pipeline(
        task_id=req.task_id,
        subject=req.subject,
        script=req.script,
        keywords=req.keywords,
        shots=req.shots,
        mode=req.mode,
        aspect=req.aspect,
        clip_duration=req.clip_duration,
        subtitle_config=req.subtitle_config,
        bgm_config=req.bgm_config,
    ))
    return {"task_id": req.task_id, "status": "started"}


@app.get("/pipeline/{task_id}/status")
async def get_pipeline_status(task_id: str):
    """Get pipeline task status."""
    from services.pipeline_service import get_task
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.to_dict()


@app.get("/pipeline/tasks")
async def list_tasks():
    """List all pipeline tasks."""
    from services.pipeline_service import get_all_tasks
    return {"tasks": get_all_tasks()}


@app.get("/video/{task_id}")
async def get_video(task_id: str):
    """Download generated video file."""
    from services.pipeline_service import get_task
    task = get_task(task_id)
    if not task or not task.video_path:
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(task.video_path, media_type="video/mp4")


class AIGCRequest(BaseModel):
    prompt: str
    adapter: str = "dreamina"
    duration: int = 5
    ratio: str = "9:16"
    api_key: str = ""
    base_url: str = ""


@app.post("/aigc/generate")
async def aigc_generate(req: AIGCRequest):
    """Generate video using AIGC adapter."""
    from services.aigc.registry import registry
    try:
        adapter = registry.get(req.adapter)
        # Update adapter config if provided
        if req.api_key:
            adapter.api_key = req.api_key
        if req.base_url:
            adapter.base_url = req.base_url
        handle = await adapter.text2video(req.prompt, req.duration, req.ratio)
        return {"submit_id": handle.submit_id, "adapter": handle.adapter_name}
    except Exception as e:
        logger.error(f"AIGC generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/aigc/adapters")
async def list_adapters():
    """List available AIGC adapters."""
    from services.aigc.registry import registry
    return {"adapters": registry.available}


@app.get("/aigc/status/{adapter}/{submit_id}")
async def aigc_status(adapter: str, submit_id: str):
    """Check AIGC task status."""
    from services.aigc.registry import registry
    from services.aigc.base import TaskHandle
    try:
        adp = registry.get(adapter)
        handle = TaskHandle(submit_id=submit_id, adapter_name=adapter)
        result = await adp.query_result(handle)
        return {
            "status": result.status,
            "file_path": result.file_path,
            "error": result.error,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Config endpoint ---

@app.put("/config")
async def update_config(config: dict):
    """Update runtime configuration (called from frontend on settings save)."""
    from services.llm_service import update_config as update_llm_config
    try:
        update_llm_config(config)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Config update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Agent endpoints ---

class AgentStartRequest(BaseModel):
    task_id: str
    subject: str


class AgentDirectionRequest(BaseModel):
    task_id: str
    direction_id: int


class AgentScriptRequest(BaseModel):
    task_id: str
    script: Optional[dict] = None


class AgentStoryboardRequest(BaseModel):
    task_id: str


@app.post("/agent/start")
async def agent_start(req: AgentStartRequest):
    """Start agent session - runs Director Agent."""
    from services.agents.orchestrator import orchestrator
    try:
        session = await orchestrator.start(req.task_id, req.subject)
        return session.to_dict()
    except Exception as e:
        logger.error(f"Agent start failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agent/direction")
async def agent_submit_direction(req: AgentDirectionRequest):
    """User chose a direction - runs ScriptWriter Agent."""
    from services.agents.orchestrator import orchestrator
    try:
        session = await orchestrator.submit_direction(req.task_id, req.direction_id)
        return session.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Agent direction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agent/script")
async def agent_submit_script(req: AgentScriptRequest):
    """User confirmed script - runs Storyboard Agent."""
    from services.agents.orchestrator import orchestrator
    try:
        session = await orchestrator.submit_script(req.task_id, req.script)
        return session.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Agent script failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agent/storyboard")
async def agent_submit_storyboard(req: AgentStoryboardRequest):
    """User confirmed storyboard - ready for video generation."""
    from services.agents.orchestrator import orchestrator
    try:
        session = await orchestrator.submit_storyboard(req.task_id)
        return session.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Agent storyboard failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agent/{task_id}")
async def agent_status(task_id: str):
    """Get agent session status."""
    from services.agents.orchestrator import orchestrator
    session = orchestrator.get_session(task_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.to_dict()


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("SIDECAR_PORT", "9527"))
    logger.info(f"Starting sidecar on port {port}")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
