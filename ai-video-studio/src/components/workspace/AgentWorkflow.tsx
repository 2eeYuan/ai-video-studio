import { useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Loader2, Sparkles, ArrowLeft, Play, FileText, Layout } from "lucide-react";
import { agentApi } from "@/lib/api";
import type { AgentStatus, AgentScript, AgentStoryboard } from "@/lib/api";
import { DirectionSelector } from "./DirectionSelector";
import { StoryboardViewer } from "./StoryboardViewer";
import { toast } from "sonner";

interface AgentWorkflowProps {
  onStartPipeline: (script: AgentScript | null, subject: string, storyboard: AgentStoryboard | null) => void;
}

type WorkflowStage = "input" | "direction" | "script" | "storyboard" | "generating";

export function AgentWorkflow({ onStartPipeline }: AgentWorkflowProps) {
  const { t } = useTranslation();
  const [subject, setSubject] = useState("");
  const [stage, setStage] = useState<WorkflowStage>("input");
  const [loading, setLoading] = useState(false);
  const [agentStatus, setAgentStatus] = useState<AgentStatus | null>(null);

  const handleStart = async () => {
    if (!subject.trim()) return;
    setLoading(true);
    try {
      const status = await agentApi.start(subject.trim());
      setAgentStatus(status);
      setStage("direction");
    } catch (e: any) {
      toast.error("启动失败: " + (e?.toString() || "未知错误"));
    } finally {
      setLoading(false);
    }
  };

  const handleSelectDirection = async (directionId: number) => {
    if (!agentStatus) return;
    setLoading(true);
    try {
      const status = await agentApi.submitDirection(agentStatus.task_id, directionId);
      setAgentStatus(status);
      setStage("script");
    } catch (e: any) {
      toast.error("生成剧本失败: " + (e?.toString() || "未知错误"));
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmScript = async () => {
    if (!agentStatus) return;
    setLoading(true);
    try {
      // Call submitScript to trigger Storyboard Agent (not submitStoryboard)
      const status = await agentApi.submitScript(agentStatus.task_id);
      setAgentStatus(status);
      setStage("storyboard");
    } catch (e: any) {
      toast.error("生成分镜失败: " + (e?.toString() || "未知错误"));
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmStoryboard = async () => {
    if (!agentStatus) return;
    setLoading(true);
    try {
      // Confirm storyboard, then start pipeline
      const status = await agentApi.submitStoryboard(agentStatus.task_id);
      setAgentStatus(status);
      onStartPipeline(agentStatus.script!, subject, agentStatus.storyboard);
      setStage("generating");
    } catch (e: any) {
      toast.error("确认分镜失败: " + (e?.toString() || "未知错误"));
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    if (stage === "script") setStage("direction");
    else if (stage === "storyboard") setStage("script");
    else if (stage === "direction") setStage("input");
  };

  const stageLabels: Record<WorkflowStage, string> = {
    input: "输入主题",
    direction: "选择方向",
    script: "确认剧本",
    storyboard: "确认分镜",
    generating: "生成视频",
  };

  return (
    <div className="flex flex-col h-full">
      {/* Stage indicator */}
      {stage !== "input" && (
        <div className="flex items-center gap-2 px-4 py-2 border-b bg-muted/30">
          <Button variant="ghost" size="icon" className="w-6 h-6" onClick={handleBack}>
            <ArrowLeft className="w-3 h-3" />
          </Button>
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            {(["direction", "script", "storyboard"] as const).map((s, i) => (
              <span key={s} className="flex items-center gap-1">
                {i > 0 && <span className="mx-1">→</span>}
                <Badge
                  variant={stage === s ? "default" : "secondary"}
                  className="text-[10px] px-1.5 py-0"
                >
                  {stageLabels[s]}
                </Badge>
              </span>
            ))}
          </div>
          {agentStatus?.chosen_direction && (
            <Badge variant="outline" className="ml-auto text-[10px]">
              {agentStatus.chosen_direction.label}
            </Badge>
          )}
        </div>
      )}

      {/* Content area */}
      <div className="flex-1 overflow-y-auto p-4">
        {/* Stage: Input */}
        {stage === "input" && (
          <div className="flex flex-col items-center justify-center h-full max-w-md mx-auto gap-6">
            <div className="text-center space-y-2">
              <Sparkles className="w-10 h-10 mx-auto text-primary" />
              <h2 className="text-lg font-semibold">AI 视频创作</h2>
              <p className="text-sm text-muted-foreground">
                输入主题，AI 将引导你完成从创意到视频的全流程
              </p>
            </div>
            <div className="w-full space-y-3">
              <Input
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="输入视频主题，例如：末世囤货、职场生存指南..."
                onKeyDown={(e) => e.key === "Enter" && handleStart()}
                className="text-center text-base h-12"
              />
              <Button
                className="w-full h-10"
                onClick={handleStart}
                disabled={loading || !subject.trim()}
              >
                {loading ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Sparkles className="w-4 h-4 mr-2" />
                )}
                开始创作
              </Button>
            </div>
          </div>
        )}

        {/* Stage: Direction Selection */}
        {stage === "direction" && (
          <DirectionSelector
            directions={agentStatus?.directions || []}
            onSelect={handleSelectDirection}
            loading={loading}
          />
        )}

        {/* Stage: Script Preview */}
        {stage === "script" && agentStatus?.script && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-primary" />
                <span className="text-sm font-medium">剧本预览</span>
              </div>
              <Button size="sm" onClick={handleConfirmScript} disabled={loading}>
                {loading ? (
                  <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                ) : (
                  <Layout className="w-3 h-3 mr-1" />
                )}
                确认剧本，生成分镜
              </Button>
            </div>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">{agentStatus.script.title}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Characters */}
                {agentStatus.script.characters?.length > 0 && (
                  <div>
                    <h4 className="text-xs font-medium text-muted-foreground mb-2">角色</h4>
                    <div className="flex flex-wrap gap-2">
                      {agentStatus.script.characters.map((c, i) => (
                        <Badge key={i} variant="secondary" className="text-xs">
                          {c.name} · {c.identity}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Scenes */}
                <div className="space-y-3">
                  {agentStatus.script.scenes?.map((scene, i) => (
                    <div key={i} className="border rounded-lg p-3 space-y-2">
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <Badge variant="outline" className="text-[10px]">
                          场景 {scene.scene_number}
                        </Badge>
                        <span>{scene.location}</span>
                        <span>·</span>
                        <span>{scene.time}</span>
                        <span>·</span>
                        <span>{scene.interior ? "内景" : "外景"}</span>
                      </div>
                      <p className="text-sm">{scene.actions}</p>
                      {scene.narration && (
                        <p className="text-sm text-primary italic border-l-2 border-primary/30 pl-2">
                          旁白：{scene.narration}
                        </p>
                      )}
                      {scene.dialogue?.length > 0 && (
                        <div className="space-y-1">
                          {scene.dialogue.map((d, j) => (
                            <div key={j} className="text-xs">
                              <span className="font-medium">{d.character}：</span>
                              <span>{d.line}</span>
                              {d.direction && (
                                <span className="text-muted-foreground ml-1">（{d.direction}）</span>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Stage: Storyboard */}
        {stage === "storyboard" && agentStatus?.storyboard && (
          <StoryboardViewer
            shots={agentStatus.storyboard.shots}
            totalDuration={agentStatus.storyboard.total_duration}
            onConfirm={handleConfirmStoryboard}
            loading={loading}
          />
        )}

        {/* Stage: Generating */}
        {stage === "generating" && (
          <div className="flex flex-col items-center justify-center h-full gap-4">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground">视频生成中，请在右侧预览区查看进度...</p>
          </div>
        )}
      </div>
    </div>
  );
}
