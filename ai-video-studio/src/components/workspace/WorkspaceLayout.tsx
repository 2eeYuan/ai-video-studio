import { useState } from "react";
import { useTranslation } from "react-i18next";
import { ScriptPanel } from "./ScriptPanel";
import { MaterialPanel } from "./MaterialPanel";
import { SubtitlePanel } from "./SubtitlePanel";
import { VideoPreview } from "./VideoPreview";
import { AgentWorkflow } from "./AgentWorkflow";
import { Sparkles } from "lucide-react";
import type { AgentScript, AgentStoryboard, AgentShot } from "@/lib/api";

export interface SubtitleConfig {
  enabled: boolean;
  font: string;
  position: string;
  fontSize: number;
  strokeWidth: number;
  fontColor: string;
  strokeColor: string;
  bgEnabled: boolean;
}

export interface BgmConfig {
  type: string;
  volume: number;
  rate: number;
}

export function WorkspaceLayout() {
  const { t } = useTranslation();
  const [subject, setSubject] = useState("");
  const [script, setScript] = useState("");
  const [keywords, setKeywords] = useState("");
  const [shots, setShots] = useState<AgentShot[]>([]);
  const [activeTab, setActiveTab] = useState<"ai" | "script" | "material" | "subtitle">("ai");

  // Subtitle & BGM config (shared between SubtitlePanel and VideoPreview)
  const [subtitleConfig, setSubtitleConfig] = useState<SubtitleConfig>({
    enabled: true,
    font: "MicrosoftYaHeiBold.ttc",
    position: "bottom",
    fontSize: 60,
    strokeWidth: 1.5,
    fontColor: "#FFFFFF",
    strokeColor: "#000000",
    bgEnabled: true,
  });
  const [bgmConfig, setBgmConfig] = useState<BgmConfig>({
    type: "random",
    volume: 0.2,
    rate: 1.0,
  });

  const handleAgentStartPipeline = (agentScript: AgentScript | null, subj: string, storyboard: AgentStoryboard | null) => {
    // Extract narration from script
    const narration = agentScript?.scenes
      ?.map((s) => s.narration || "")
      .filter(Boolean)
      .join("\n");
    setSubject(subj);
    setScript(narration || agentScript?.title || "");
    // Store storyboard shots for AIGC pipeline
    if (storyboard?.shots) {
      setShots(storyboard.shots);
    }
    setActiveTab("material");
  };

  return (
    <div className="flex flex-col h-[calc(100vh-3rem)]">
      <div className="flex flex-1 overflow-hidden">
        {/* Tab Selector */}
        <div className="w-12 border-r bg-muted/30 flex flex-col items-center pt-2 gap-1">
          <button
            onClick={() => setActiveTab("ai")}
            className={`w-10 h-10 rounded-md text-xs font-medium transition-colors flex items-center justify-center ${
              activeTab === "ai"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-accent"
            }`}
            title="AI 创作"
          >
            <Sparkles className="w-4 h-4" />
          </button>
          {(["script", "material", "subtitle"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`w-10 h-10 rounded-md text-xs font-medium transition-colors ${
                activeTab === tab
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent"
              }`}
            >
              {t(`workspace.${tab}`)}
            </button>
          ))}
        </div>

        {/* Left Panel */}
        <div className="w-72 border-r overflow-hidden">
          {activeTab === "ai" && (
            <AgentWorkflow onStartPipeline={handleAgentStartPipeline} />
          )}
          {activeTab === "script" && (
            <ScriptPanel
              subject={subject}
              onSubjectChange={setSubject}
              script={script}
              onScriptChange={setScript}
              keywords={keywords}
              onKeywordsChange={setKeywords}
            />
          )}
          {activeTab === "material" && (
            <MaterialPanel shots={shots} />
          )}
          {activeTab === "subtitle" && (
            <SubtitlePanel
              subtitleConfig={subtitleConfig}
              onSubtitleConfigChange={setSubtitleConfig}
              bgmConfig={bgmConfig}
              onBgmConfigChange={setBgmConfig}
            />
          )}
        </div>

        {/* Right: Video Preview */}
        <div className="flex-1">
          <VideoPreview
            subject={subject}
            script={script}
            keywords={keywords}
            shots={shots}
            subtitleConfig={subtitleConfig}
            bgmConfig={bgmConfig}
          />
        </div>
      </div>
    </div>
  );
}
