import { invoke } from "@tauri-apps/api/core";
import type { Project } from "@/types";

export const projectApi = {
  getAll: async (): Promise<Project[]> => {
    const json = await invoke<string>("get_projects");
    return JSON.parse(json);
  },
  create: async (name: string, subject: string): Promise<Project> => {
    const json = await invoke<string>("create_project", { name, subject });
    return JSON.parse(json);
  },
  delete: async (id: string): Promise<void> => {
    await invoke("delete_project", { id });
  },
};

export interface ScriptResponse {
  script: string;
  keywords: string[];
}

export interface PipelineStatus {
  task_id: string;
  status: string;
  progress: number;
  message: string;
  video_path: string | null;
  error: string | null;
}

export const sidecarApi = {
  start: async (): Promise<void> => {
    await invoke("start_sidecar");
  },
  status: async (): Promise<boolean> => {
    return await invoke("sidecar_status");
  },
  generateScript: async (
    subject: string,
    language: string = "zh-CN",
    paragraphNumber: number = 6,
    customPrompt: string = ""
  ): Promise<ScriptResponse> => {
    const json = await invoke<string>("ai_generate_script", {
      subject,
      language,
      paragraphNumber,
      customPrompt,
    });
    return JSON.parse(json);
  },
  generateTerms: async (
    subject: string,
    script: string
  ): Promise<string[]> => {
    const json = await invoke<string>("ai_generate_terms", {
      subject,
      script,
    });
    return JSON.parse(json);
  },
  startPipeline: async (params: {
    taskId: string;
    subject: string;
    script: string;
    keywords: string;
    shots?: AgentShot[];
  }): Promise<void> => {
    await invoke("ai_start_pipeline", {
      taskId: params.taskId,
      subject: params.subject,
      script: params.script,
      keywords: params.keywords,
      shots: params.shots ?? null,
    });
  },
  getPipelineStatus: async (taskId: string): Promise<PipelineStatus> => {
    const json = await invoke<string>("ai_pipeline_status", { taskId });
    return JSON.parse(json);
  },
  getVideoUrl: async (taskId: string): Promise<string> => {
    return await invoke<string>("get_video_url", { taskId });
  },
  exportVideo: async (sourcePath: string, destPath: string): Promise<void> => {
    await invoke("export_video", { sourcePath, destPath });
  },
};

export const settingsApi = {
  writeSidecarConfig: async (sidecarDir: string, settings: Record<string, unknown>): Promise<void> => {
    await invoke("write_sidecar_config", { sidecarDir, settings });
  },
};

// --- Agent API ---

export interface AgentDirection {
  id: number;
  label: string;
  concept: string;
  description: string;
}

export interface AgentCharacter {
  name: string;
  identity: string;
  traits: string;
}

export interface AgentScene {
  scene_number: number;
  location: string;
  time: string;
  interior: boolean;
  actions: string;
  narration?: string;
  dialogue: { character: string; line: string; direction?: string }[];
}

export interface AgentScript {
  title: string;
  characters: AgentCharacter[];
  scenes: AgentScene[];
}

export interface AgentShot {
  shot_id: string;
  shot_type: string;
  angle: string;
  description: string;
  narration_segment?: string;
  sound: string;
  camera_movement: string;
  duration: number;
  references?: string[];
}

export interface AgentStoryboard {
  shots: AgentShot[];
  total_duration?: number;
}

export interface AgentStatus {
  task_id: string;
  stage: string;
  subject: string;
  directions: AgentDirection[] | null;
  chosen_direction: AgentDirection | null;
  script: AgentScript | null;
  storyboard: AgentStoryboard | null;
  status: string;
  error: string | null;
}

export const agentApi = {
  start: async (subject: string): Promise<AgentStatus> => {
    const json = await invoke<string>("agent_start", { subject });
    return JSON.parse(json);
  },
  submitDirection: async (taskId: string, directionId: number): Promise<AgentStatus> => {
    const json = await invoke<string>("agent_submit_direction", { taskId, directionId });
    return JSON.parse(json);
  },
  submitScript: async (taskId: string, script?: string): Promise<AgentStatus> => {
    const json = await invoke<string>("agent_submit_script", { taskId, script });
    return JSON.parse(json);
  },
  submitStoryboard: async (taskId: string): Promise<AgentStatus> => {
    const json = await invoke<string>("agent_submit_storyboard", { taskId });
    return JSON.parse(json);
  },
  status: async (taskId: string): Promise<AgentStatus> => {
    const json = await invoke<string>("agent_status", { taskId });
    return JSON.parse(json);
  },
};
