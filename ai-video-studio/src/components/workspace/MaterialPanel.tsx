import { useState, useEffect, useRef, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { Store } from "@tauri-apps/plugin-store";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { Image, Sparkles, Loader2, Settings, ChevronDown, ChevronUp, RotateCcw, Clock, CheckCircle2, XCircle } from "lucide-react";
import type { AgentShot } from "@/lib/api";

interface AIGCTool {
  value: string;
  label: string;
  needsKey: boolean;
  baseUrl?: string;
}

const AIGC_TOOLS: AIGCTool[] = [
  { value: "dreamina", label: "即梦 (Dreamina)", needsKey: true, baseUrl: "https://jimeng.jianying.com" },
  { value: "kling", label: "可灵 (Kling)", needsKey: true, baseUrl: "https://api.klingai.com" },
  { value: "runway", label: "Runway", needsKey: true, baseUrl: "https://api.runwayml.com" },
  { value: "pika", label: "Pika", needsKey: true, baseUrl: "https://api.pika.art" },
  { value: "luma", label: "Luma Dream Machine", needsKey: true, baseUrl: "https://api.lumalabs.ai" },
  { value: "cogvideo", label: "CogVideoX (开源)", needsKey: false },
];

interface ShotClip {
  shotId: string;
  status: "idle" | "submitting" | "polling" | "done" | "failed";
  videoUrl?: string;
  submitId?: string;
  error?: string;
}

interface MaterialPanelProps {
  shots: AgentShot[];
}

export function MaterialPanel({ shots }: MaterialPanelProps) {
  const { t } = useTranslation();
  const [aigcAdapter, setAigcAdapter] = useState("dreamina");
  const [showApiSettings, setShowApiSettings] = useState(false);
  const [aigcApiKey, setAigcApiKey] = useState("");
  const [aigcBaseUrl, setAigcBaseUrl] = useState("");
  const [shotClips, setShotClips] = useState<Record<string, ShotClip>>({});
  const pollTimers = useRef<Record<string, ReturnType<typeof setInterval>>>({});

  // Load AIGC settings from store
  useEffect(() => {
    (async () => {
      try {
        const store = await Store.load("settings.json");
        const aigc = await store.get<Record<string, string>>("aigc");
        if (aigc) {
          if (aigc.adapter) setAigcAdapter(aigc.adapter);
          if (aigc.apiKey) setAigcApiKey(aigc.apiKey);
          if (aigc.baseUrl) setAigcBaseUrl(aigc.baseUrl);
        }
      } catch (e) {
        console.error("Failed to load AIGC settings:", e);
      }
    })();
  }, []);

  // Cleanup poll timers on unmount
  useEffect(() => {
    return () => {
      Object.values(pollTimers.current).forEach(clearInterval);
    };
  }, []);

  const handleAdapterChange = (adapter: string) => {
    setAigcAdapter(adapter);
    const tool = AIGC_TOOLS.find((t) => t.value === adapter);
    if (tool?.baseUrl) setAigcBaseUrl(tool.baseUrl);
  };

  const handleSaveApiSettings = async () => {
    try {
      const store = await Store.load("settings.json");
      await store.set("aigc", {
        adapter: aigcAdapter,
        apiKey: aigcApiKey,
        baseUrl: aigcBaseUrl,
      });
      await store.save();
      setShowApiSettings(false);
    } catch (e) {
      console.error("Failed to save AIGC settings:", e);
    }
  };

  const pollShotResult = useCallback((shotId: string, adapter: string, submitId: string) => {
    // Clear existing timer
    if (pollTimers.current[shotId]) clearInterval(pollTimers.current[shotId]);

    let attempts = 0;
    pollTimers.current[shotId] = setInterval(async () => {
      attempts++;
      if (attempts > 60) {
        // Timeout after ~5 minutes
        clearInterval(pollTimers.current[shotId]);
        delete pollTimers.current[shotId];
        setShotClips((prev) => ({
          ...prev,
          [shotId]: { ...prev[shotId], status: "failed", error: "生成超时" },
        }));
        return;
      }

      try {
        const resp = await fetch(`http://127.0.0.1:9527/aigc/status/${adapter}/${submitId}`);
        if (!resp.ok) return;
        const data = await resp.json();

        if (data.status === "success" && data.file_path) {
          clearInterval(pollTimers.current[shotId]);
          delete pollTimers.current[shotId];
          // Construct video URL from file path
          const videoUrl = `http://127.0.0.1:9527/video/file?path=${encodeURIComponent(data.file_path)}`;
          setShotClips((prev) => ({
            ...prev,
            [shotId]: { ...prev[shotId], status: "done", videoUrl },
          }));
        } else if (data.status === "failed") {
          clearInterval(pollTimers.current[shotId]);
          delete pollTimers.current[shotId];
          setShotClips((prev) => ({
            ...prev,
            [shotId]: { ...prev[shotId], status: "failed", error: data.error || "生成失败" },
          }));
        }
      } catch (e) {
        console.error(`Poll failed for shot ${shotId}:`, e);
      }
    }, 5000);
  }, []);

  const handleGenerateShot = async (shot: AgentShot) => {
    const prompt = `${shot.description} ${shot.narration_segment || ""}`.trim();
    if (!prompt) return;

    setShotClips((prev) => ({
      ...prev,
      [shot.shot_id]: { shotId: shot.shot_id, status: "submitting" },
    }));

    try {
      const resp = await fetch("http://127.0.0.1:9527/aigc/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt,
          adapter: aigcAdapter,
          duration: shot.duration,
          ratio: "9:16",
          api_key: aigcApiKey,
          base_url: aigcBaseUrl,
        }),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();

      setShotClips((prev) => ({
        ...prev,
        [shot.shot_id]: {
          ...prev[shot.shot_id],
          status: "polling",
          submitId: data.submit_id,
        },
      }));

      // Start polling
      pollShotResult(shot.shot_id, aigcAdapter, data.submit_id);
    } catch (e: any) {
      setShotClips((prev) => ({
        ...prev,
        [shot.shot_id]: { ...prev[shot.shot_id], status: "failed", error: e.toString() },
      }));
    }
  };

  const handleGenerateAll = async () => {
    for (const shot of shots) {
      const clip = shotClips[shot.shot_id];
      if (!clip || clip.status === "idle" || clip.status === "failed") {
        await handleGenerateShot(shot);
      }
    }
  };

  const selectedTool = AIGC_TOOLS.find((t) => t.value === aigcAdapter);
  const doneCount = Object.values(shotClips).filter((c) => c.status === "done").length;
  const generatingCount = Object.values(shotClips).filter(
    (c) => c.status === "submitting" || c.status === "polling"
  ).length;

  return (
    <div className="flex flex-col h-full overflow-y-auto p-3 gap-3">
      {/* AIGC Tool Selection + API Settings */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">AIGC 视频生成</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="space-y-1">
            <Label className="text-xs">AIGC 工具</Label>
            <Select
              value={aigcAdapter}
              onChange={(e) => handleAdapterChange(e.target.value)}
              options={AIGC_TOOLS.map((t) => ({ value: t.value, label: t.label }))}
            />
          </div>

          <button
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors w-full"
            onClick={() => setShowApiSettings(!showApiSettings)}
          >
            <Settings className="w-3 h-3" />
            <span>API 配置 {selectedTool?.needsKey ? "(需要 API Key)" : "(无需 Key)"}</span>
            {showApiSettings ? <ChevronUp className="w-3 h-3 ml-auto" /> : <ChevronDown className="w-3 h-3 ml-auto" />}
          </button>

          {showApiSettings && (
            <>
              <Separator />
              {selectedTool?.needsKey && (
                <div className="space-y-1">
                  <Label className="text-xs">API Key</Label>
                  <Input
                    type="password"
                    value={aigcApiKey}
                    onChange={(e) => setAigcApiKey(e.target.value)}
                    placeholder={`${selectedTool.label} API Key`}
                  />
                </div>
              )}
              <div className="space-y-1">
                <Label className="text-xs">Base URL</Label>
                <Input
                  value={aigcBaseUrl}
                  onChange={(e) => setAigcBaseUrl(e.target.value)}
                  placeholder={selectedTool?.baseUrl || "https://api.example.com"}
                />
              </div>
              <Button size="sm" variant="outline" className="w-full" onClick={handleSaveApiSettings}>
                保存 API 配置
              </Button>
            </>
          )}
        </CardContent>
      </Card>

      {/* Shots List */}
      <Card className="flex-1">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm">
              分镜生成
              {shots.length > 0 && (
                <span className="text-xs text-muted-foreground ml-2">
                  {doneCount}/{shots.length} 完成
                </span>
              )}
            </CardTitle>
            {shots.length > 0 && (
              <Button
                size="sm"
                variant="outline"
                onClick={handleGenerateAll}
                disabled={generatingCount > 0 || (selectedTool?.needsKey && !aigcApiKey)}
              >
                <Sparkles className="w-3 h-3 mr-1" />
                全部生成
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {shots.length === 0 ? (
            <div className="text-center text-muted-foreground py-8">
              <Image className="w-8 h-8 mx-auto mb-2 opacity-20" />
              <p className="text-sm">请先在 AI 创作中生成分镜表</p>
            </div>
          ) : (
            <div className="space-y-2">
              {shots.map((shot) => {
                const clip = shotClips[shot.shot_id];
                const isBusy = clip && (clip.status === "submitting" || clip.status === "polling");

                return (
                  <div
                    key={shot.shot_id}
                    className="border rounded-lg p-2 space-y-1.5"
                  >
                    {/* Shot header */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5">
                        <Badge variant="outline" className="text-[10px] px-1 py-0">
                          {shot.shot_id}
                        </Badge>
                        <Badge variant="secondary" className="text-[10px] px-1 py-0">
                          {shot.shot_type}
                        </Badge>
                        <span className="flex items-center gap-0.5 text-[10px] text-muted-foreground">
                          <Clock className="w-2.5 h-2.5" />
                          {shot.duration}s
                        </span>
                      </div>
                      <div className="flex items-center gap-1">
                        {clip?.status === "done" && (
                          <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
                        )}
                        {clip?.status === "failed" && (
                          <XCircle className="w-3.5 h-3.5 text-destructive" />
                        )}
                        <Button
                          size="sm"
                          variant={clip?.status === "done" ? "outline" : "default"}
                          className="h-6 px-2 text-[10px]"
                          onClick={() => handleGenerateShot(shot)}
                          disabled={isBusy || (selectedTool?.needsKey && !aigcApiKey)}
                        >
                          {isBusy ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          ) : clip?.status === "done" ? (
                            <RotateCcw className="w-3 h-3" />
                          ) : (
                            <Sparkles className="w-3 h-3" />
                          )}
                          {isBusy ? "生成中" : clip?.status === "done" ? "重新生成" : "生成"}
                        </Button>
                      </div>
                    </div>

                    {/* Description */}
                    <p className="text-xs leading-relaxed">{shot.description}</p>

                    {/* Narration */}
                    {shot.narration_segment && (
                      <p className="text-xs text-primary italic border-l-2 border-primary/30 pl-1.5">
                        旁白：{shot.narration_segment}
                      </p>
                    )}

                    {/* Video preview or error */}
                    {clip?.status === "done" && clip.videoUrl && (
                      <div className="mt-1">
                        <video
                          src={clip.videoUrl}
                          controls
                          muted
                          className="w-full max-h-40 rounded object-cover"
                        />
                      </div>
                    )}
                    {clip?.status === "failed" && clip.error && (
                      <p className="text-[10px] text-destructive">{clip.error}</p>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
