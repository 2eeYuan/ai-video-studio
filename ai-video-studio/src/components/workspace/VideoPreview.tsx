import { useState, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Play, Download, Loader2, CheckCircle2, XCircle } from "lucide-react";
import { sidecarApi } from "@/lib/api";
import type { PipelineStatus, AgentShot } from "@/lib/api";
import type { SubtitleConfig, BgmConfig } from "./WorkspaceLayout";

interface VideoPreviewProps {
  subject: string;
  script: string;
  keywords: string;
  shots: AgentShot[];
  subtitleConfig: SubtitleConfig;
  bgmConfig: BgmConfig;
}

export function VideoPreview({ subject, script, keywords, shots, subtitleConfig, bgmConfig }: VideoPreviewProps) {
  const { t } = useTranslation();
  const [taskId, setTaskId] = useState<string | null>(null);
  const [status, setStatus] = useState<string>("idle");
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState("");
  const [videoPath, setVideoPath] = useState<string | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const isGenerating =
    status === "generating_script" ||
    status === "generating_subtitle" ||
    status === "generating_video" ||
    status === "combining_video";

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const pollStatus = (id: string) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const s: PipelineStatus = await sidecarApi.getPipelineStatus(id);
        setStatus(s.status);
        setProgress(s.progress);
        setMessage(s.message);
        if (s.video_path) {
          setVideoPath(s.video_path);
          try {
            const url = await sidecarApi.getVideoUrl(id);
            setVideoUrl(url);
          } catch {}
        }
        if (s.error) setError(s.error);
        if (s.status === "done" || s.status === "failed") {
          if (pollRef.current) clearInterval(pollRef.current);
        }
      } catch (e) {
        console.error("Poll failed:", e);
      }
    }, 1500);
  };

  const handleGenerate = async () => {
    if (!subject) return;
    const id = crypto.randomUUID().slice(0, 12);
    setTaskId(id);
    setStatus("started");
    setProgress(0);
    setError(null);
    setVideoPath(null);

    try {
      // Ensure sidecar is running
      const running = await sidecarApi.status();
      if (!running) {
        await sidecarApi.start();
        // Wait for sidecar to be ready
        await new Promise((r) => setTimeout(r, 2000));
      }

      await sidecarApi.startPipeline({
        taskId: id,
        subject,
        script,
        keywords,
        shots: shots.length > 0 ? shots : undefined,
      });
      pollStatus(id);
    } catch (e: any) {
      setError(e.toString());
      setStatus("failed");
    }
  };

  const statusMessages: Record<string, string> = {
    idle: t("status.idle"),
    started: "准备中...",
    generating_script: t("status.generatingScript"),
    generating_subtitle: t("status.generatingSubtitle"),
    generating_video: t("status.generatingVideo"),
    combining_video: t("status.combiningVideo"),
    done: t("status.done"),
    failed: t("status.failed"),
  };

  return (
    <div className="flex flex-col h-full border-t bg-background">
      {/* Video Area */}
      <div className="flex-1 flex items-center justify-center bg-black/5">
        {videoUrl ? (
          <video
            src={videoUrl}
            controls
            className="max-h-full max-w-full rounded"
          />
        ) : (
          <div className="text-center text-muted-foreground">
            <Play className="w-12 h-12 mx-auto mb-2 opacity-20" />
            <p className="text-sm">视频预览区域</p>
            <p className="text-xs">生成视频后在此预览</p>
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="mx-4 p-2 bg-destructive/10 text-destructive text-xs rounded">
          {error}
        </div>
      )}

      {/* Controls */}
      <div className="flex items-center gap-3 px-4 py-2 border-t">
        <Button onClick={handleGenerate} disabled={isGenerating || !subject} className="gap-2">
          {isGenerating ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : status === "done" ? (
            <CheckCircle2 className="w-4 h-4" />
          ) : status === "failed" ? (
            <XCircle className="w-4 h-4" />
          ) : (
            <Play className="w-4 h-4" />
          )}
          {isGenerating ? t("workspace.generating") : t("workspace.generate")}
        </Button>

        <div className="flex-1">
          <Progress value={progress * 100} className="h-1.5" />
        </div>

        <span className="text-xs text-muted-foreground min-w-[120px]">
          {message || statusMessages[status] || status}
          {progress > 0 && ` ${Math.round(progress * 100)}%`}
        </span>

        <Button variant="outline" disabled={status !== "done"} onClick={async () => {
          if (!videoPath) return;
          try {
            const { save } = await import("@tauri-apps/plugin-dialog");
            const dest = await save({
              defaultPath: "video.mp4",
              filters: [{ name: "Video", extensions: ["mp4"] }],
            });
            if (dest) {
              await sidecarApi.exportVideo(videoPath, dest);
            }
          } catch (e) {
            console.error("Export failed:", e);
          }
        }}>
          <Download className="w-4 h-4 mr-1" />
          {t("workspace.export")}
        </Button>
      </div>
    </div>
  );
}
