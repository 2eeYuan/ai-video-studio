export interface Project {
  id: string;
  name: string;
  subject: string;
  mode: "material" | "aigc";
  script: string;
  keywords: string;
  aspect: string;
  status: "draft" | "generating" | "done" | "failed";
  params: string;
  created_at: string;
  updated_at: string;
}

export type VideoMode = "material" | "aigc";
export type AspectRatio = "16:9" | "9:16" | "1:1";
export type ConcatMode = "random" | "sequential";
export type TransitionMode = "none" | "fade_in" | "fade_out" | "shuffle";

export interface LLMSettings {
  provider: string;
  api_key: string;
  base_url: string;
  model: string;
}

export interface TTSSettings {
  voice: string;
}

export interface AppSettings {
  llm: LLMSettings;
  tts: TTSSettings;
}
