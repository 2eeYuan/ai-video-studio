import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Store } from "@tauri-apps/plugin-store";
import { invoke } from "@tauri-apps/api/core";
import { toast } from "sonner";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import {
  Settings,
  X,
  Globe,
  Volume2,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Copy,
  ClipboardPaste,
} from "lucide-react";

interface SettingsDialogProps {
  open: boolean;
  onClose: () => void;
}

export function SettingsDialog({ open, onClose }: SettingsDialogProps) {
  const { t } = useTranslation();

  // LLM state
  const [llmProvider, setLlmProvider] = useState("openai");
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("https://api.openai.com/v1");
  const [model, setModel] = useState("gpt-4o-mini");

  // TTS state
  const [ttsProvider, setTtsProvider] = useState("edge-tts");
  const [edgeVoice, setEdgeVoice] = useState("zh-CN-YunxiNeural");
  const [edgeRate, setEdgeRate] = useState("1.0");
  const [edgeVolume, setEdgeVolume] = useState("1.0");
  const [openaiTtsKey, setOpenaiTtsKey] = useState("");
  const [openaiTtsBaseUrl, setOpenaiTtsBaseUrl] = useState("https://api.openai.com/v1");
  const [openaiTtsModel, setOpenaiTtsModel] = useState("tts-1");
  const [openaiTtsVoice, setOpenaiTtsVoice] = useState("alloy");
  const [azureKey, setAzureKey] = useState("");
  const [azureRegion, setAzureRegion] = useState("eastasia");
  const [azureVoice, setAzureVoice] = useState("zh-CN-YunxiNeural");
  const [fishKey, setFishKey] = useState("");
  const [fishBaseUrl, setFishBaseUrl] = useState("https://api.fish.audio/v1");
  const [fishModel, setFishModel] = useState("");
  const [fishVoice, setFishVoice] = useState("");
  // Custom TTS state
  const [customTtsKey, setCustomTtsKey] = useState("");
  const [customTtsBaseUrl, setCustomTtsBaseUrl] = useState("");
  const [customTtsModel, setCustomTtsModel] = useState("");
  const [customTtsVoice, setCustomTtsVoice] = useState("");

  // JSON config import/export
  const [jsonConfig, setJsonConfig] = useState("");
  const [showJsonPanel, setShowJsonPanel] = useState(false);

  // Test connection state
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<"ok" | "fail" | null>(null);

  const providerDefaults: Record<string, { baseUrl: string; model: string }> = {
    openai: { baseUrl: "https://api.openai.com/v1", model: "gpt-4o-mini" },
    deepseek: { baseUrl: "https://api.deepseek.com", model: "deepseek-chat" },
    mimo: { baseUrl: "https://token-plan-cn.xiaomimimo.com/v1", model: "mimo-v2.5-pro" },
    moonshot: { baseUrl: "https://api.moonshot.cn/v1", model: "moonshot-v1-8k" },
    qwen: { baseUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1", model: "qwen-max" },
    zhipu: { baseUrl: "https://open.bigmodel.cn/api/paas/v4", model: "glm-4-flash" },
    minimax: { baseUrl: "https://api.minimax.chat/v1", model: "MiniMax-Text-01" },
    yi: { baseUrl: "https://api.lingyiwanwu.com/v1", model: "yi-large" },
  };

  // Load saved settings when dialog opens
  useEffect(() => {
    if (!open) return;
    (async () => {
      try {
        const store = await Store.load("settings.json");

        const llm = await store.get<Record<string, string>>("llm");
        if (llm) {
          if (llm.provider) setLlmProvider(llm.provider);
          if (llm.apiKey) setApiKey(llm.apiKey);
          if (llm.baseUrl) setBaseUrl(llm.baseUrl);
          if (llm.model) setModel(llm.model);
        }

        const tts = await store.get<Record<string, string>>("tts");
        if (tts) {
          if (tts.provider) setTtsProvider(tts.provider);
          if (tts.edgeVoice) setEdgeVoice(tts.edgeVoice);
          if (tts.edgeRate) setEdgeRate(tts.edgeRate);
          if (tts.edgeVolume) setEdgeVolume(tts.edgeVolume);
          if (tts.openaiKey) setOpenaiTtsKey(tts.openaiKey);
          if (tts.openaiBaseUrl) setOpenaiTtsBaseUrl(tts.openaiBaseUrl);
          if (tts.openaiModel) setOpenaiTtsModel(tts.openaiModel);
          if (tts.openaiVoice) setOpenaiTtsVoice(tts.openaiVoice);
          if (tts.azureKey) setAzureKey(tts.azureKey);
          if (tts.azureRegion) setAzureRegion(tts.azureRegion);
          if (tts.azureVoice) setAzureVoice(tts.azureVoice);
          if (tts.fishKey) setFishKey(tts.fishKey);
          if (tts.fishBaseUrl) setFishBaseUrl(tts.fishBaseUrl);
          if (tts.fishModel) setFishModel(tts.fishModel);
          if (tts.fishVoice) setFishVoice(tts.fishVoice);
          if (tts.customKey) setCustomTtsKey(tts.customKey);
          if (tts.customBaseUrl) setCustomTtsBaseUrl(tts.customBaseUrl);
          if (tts.customModel) setCustomTtsModel(tts.customModel);
          if (tts.customVoice) setCustomTtsVoice(tts.customVoice);
        }
      } catch (e) {
        console.error("Failed to load settings:", e);
      }
    })();
  }, [open]);

  const handleProviderChange = (provider: string) => {
    setLlmProvider(provider);
    if (provider === "custom") return; // Don't auto-fill for custom
    const defaults = providerDefaults[provider];
    if (defaults) {
      setBaseUrl(defaults.baseUrl);
      setModel(defaults.model);
    }
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      // Step 1: Ensure sidecar is running
      let sidecarRunning = false;
      try {
        const healthResp = await fetch("http://127.0.0.1:9527/health", { signal: AbortSignal.timeout(3000) });
        sidecarRunning = healthResp.ok;
      } catch {
        // Sidecar not running, try to start it
        try {
          await invoke("start_sidecar");
          // Wait for sidecar to be ready
          for (let i = 0; i < 10; i++) {
            await new Promise((r) => setTimeout(r, 1000));
            try {
              const hr = await fetch("http://127.0.0.1:9527/health", { signal: AbortSignal.timeout(2000) });
              if (hr.ok) { sidecarRunning = true; break; }
            } catch {}
          }
        } catch {}
      }

      if (!sidecarRunning) {
        setTestResult("fail");
        return;
      }

      // Step 2: Push current config to sidecar runtime
      await fetch("http://127.0.0.1:9527/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          llm: { provider: llmProvider, api_key: apiKey, base_url: baseUrl, model },
        }),
      });

      // Step 3: Test with a minimal LLM call
      const resp = await fetch("http://127.0.0.1:9527/generate/script", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ subject: "test", language: "en", paragraph_number: 1 }),
      });
      setTestResult(resp.ok ? "ok" : "fail");
    } catch {
      setTestResult("fail");
    } finally {
      setTesting(false);
    }
  };

  const buildSettingsJson = () => {
    return JSON.stringify({
      llm: { provider: llmProvider, apiKey, baseUrl, model },
      tts: {
        provider: ttsProvider,
        edgeVoice, edgeRate, edgeVolume,
        openaiKey: openaiTtsKey, openaiBaseUrl: openaiTtsBaseUrl, openaiModel: openaiTtsModel, openaiVoice: openaiTtsVoice,
        azureKey, azureRegion, azureVoice,
        fishKey, fishBaseUrl, fishModel, fishVoice,
        customKey: customTtsKey, customBaseUrl: customTtsBaseUrl, customModel: customTtsModel, customVoice: customTtsVoice,
      },
    }, null, 2);
  };

  const handleCopyConfig = async () => {
    try {
      await navigator.clipboard.writeText(buildSettingsJson());
      toast.success("配置已复制到剪贴板");
    } catch {
      setJsonConfig(buildSettingsJson());
      setShowJsonPanel(true);
    }
  };

  const handlePasteConfig = async () => {
    try {
      let text = "";
      try {
        text = await navigator.clipboard.readText();
      } catch {
        text = jsonConfig;
      }
      if (!text.trim()) {
        toast.error("剪贴板为空");
        return;
      }
      const cfg = JSON.parse(text);
      if (cfg.llm) {
        if (cfg.llm.provider) setLlmProvider(cfg.llm.provider);
        if (cfg.llm.apiKey) setApiKey(cfg.llm.apiKey);
        if (cfg.llm.baseUrl) setBaseUrl(cfg.llm.baseUrl);
        if (cfg.llm.model) setModel(cfg.llm.model);
      }
      if (cfg.tts) {
        if (cfg.tts.provider) setTtsProvider(cfg.tts.provider);
        if (cfg.tts.edgeVoice) setEdgeVoice(cfg.tts.edgeVoice);
        if (cfg.tts.edgeRate) setEdgeRate(cfg.tts.edgeRate);
        if (cfg.tts.edgeVolume) setEdgeVolume(cfg.tts.edgeVolume);
        if (cfg.tts.openaiKey) setOpenaiTtsKey(cfg.tts.openaiKey);
        if (cfg.tts.openaiBaseUrl) setOpenaiTtsBaseUrl(cfg.tts.openaiBaseUrl);
        if (cfg.tts.openaiModel) setOpenaiTtsModel(cfg.tts.openaiModel);
        if (cfg.tts.openaiVoice) setOpenaiTtsVoice(cfg.tts.openaiVoice);
        if (cfg.tts.azureKey) setAzureKey(cfg.tts.azureKey);
        if (cfg.tts.azureRegion) setAzureRegion(cfg.tts.azureRegion);
        if (cfg.tts.azureVoice) setAzureVoice(cfg.tts.azureVoice);
        if (cfg.tts.fishKey) setFishKey(cfg.tts.fishKey);
        if (cfg.tts.fishBaseUrl) setFishBaseUrl(cfg.tts.fishBaseUrl);
        if (cfg.tts.fishModel) setFishModel(cfg.tts.fishModel);
        if (cfg.tts.fishVoice) setFishVoice(cfg.tts.fishVoice);
        if (cfg.tts.customKey) setCustomTtsKey(cfg.tts.customKey);
        if (cfg.tts.customBaseUrl) setCustomTtsBaseUrl(cfg.tts.customBaseUrl);
        if (cfg.tts.customModel) setCustomTtsModel(cfg.tts.customModel);
        if (cfg.tts.customVoice) setCustomTtsVoice(cfg.tts.customVoice);
      }
      toast.success("配置已导入");
    } catch (e) {
      toast.error("JSON 格式错误，请检查");
    }
  };

  const handleSave = async () => {
    try {
      const store = await Store.load("settings.json");

      await store.set("llm", {
        provider: llmProvider,
        apiKey,
        baseUrl,
        model,
      });

      await store.set("tts", {
        provider: ttsProvider,
        edgeVoice,
        edgeRate,
        edgeVolume,
        openaiKey: openaiTtsKey,
        openaiBaseUrl: openaiTtsBaseUrl,
        openaiModel: openaiTtsModel,
        openaiVoice: openaiTtsVoice,
        azureKey,
        azureRegion,
        azureVoice,
        fishKey,
        fishBaseUrl,
        fishModel,
        fishVoice,
        customKey: customTtsKey,
        customBaseUrl: customTtsBaseUrl,
        customModel: customTtsModel,
        customVoice: customTtsVoice,
      });

      await store.save();

      // Write config.yaml for Python sidecar
      await invoke("write_sidecar_config", {
        sidecarDir: "sidecar",
        settings: {
          llm: { provider: llmProvider, api_key: apiKey, base_url: baseUrl, model },
          tts: { voice: edgeVoice },
        },
      });

      // Push config to running sidecar's runtime
      try {
        await fetch("http://127.0.0.1:9527/config", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            llm: { provider: llmProvider, api_key: apiKey, base_url: baseUrl, model },
          }),
        });
      } catch {
        // Sidecar not running yet — config.yaml will be read on next start
      }

      toast.success("设置已保存");
    } catch (e) {
      console.error("Failed to save settings:", e);
      toast.error("保存失败");
    }
    onClose();
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-background rounded-lg shadow-lg w-[540px] max-h-[85vh] flex flex-col">
        <div className="flex items-center justify-between p-4 border-b shrink-0">
          <div className="flex items-center gap-2">
            <Settings className="w-5 h-5" />
            <span className="font-semibold">{t("app.settings")}</span>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="w-4 h-4" />
          </Button>
        </div>

        <div className="p-4 space-y-4 overflow-y-auto flex-1 min-h-0">
          {/* LLM Settings */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Globe className="w-4 h-4" />
                LLM 设置
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-1">
                <Label className="text-xs">{t("settings.llmProvider")}</Label>
                <Select
                  value={llmProvider}
                  onChange={(e) => handleProviderChange(e.target.value)}
                  options={[
                    { value: "openai", label: "OpenAI" },
                    { value: "deepseek", label: "DeepSeek" },
                    { value: "mimo", label: "Xiaomi MiMo" },
                    { value: "moonshot", label: "Moonshot (Kimi)" },
                    { value: "qwen", label: "通义千问 (Qwen)" },
                    { value: "zhipu", label: "智谱 (GLM)" },
                    { value: "minimax", label: "MiniMax" },
                    { value: "yi", label: "零一万物 (Yi)" },
                    { value: "custom", label: "自定义 (Custom)" },
                  ]}
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">{t("settings.apiKey")}</Label>
                <Input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder={t("settings.openaiKeyPlaceholder")}
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">{t("settings.baseUrl")}</Label>
                <Input
                  value={baseUrl}
                  onChange={(e) => setBaseUrl(e.target.value)}
                  placeholder="https://api.example.com/v1"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">{t("settings.model")}</Label>
                <Input
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  placeholder="gpt-4o-mini"
                />
              </div>
              <Button
                variant="outline"
                size="sm"
                className="gap-1"
                onClick={handleTestConnection}
                disabled={testing}
              >
                {testing ? (
                  <RefreshCw className="w-3 h-3 animate-spin" />
                ) : testResult === "ok" ? (
                  <CheckCircle2 className="w-3 h-3 text-green-500" />
                ) : testResult === "fail" ? (
                  <XCircle className="w-3 h-3 text-red-500" />
                ) : (
                  <RefreshCw className="w-3 h-3" />
                )}
                {testing
                  ? t("settings.testing")
                  : testResult === "ok"
                  ? t("settings.connected")
                  : testResult === "fail"
                  ? t("settings.failed")
                  : t("settings.testConnection")}
              </Button>
            </CardContent>
          </Card>

          {/* TTS Settings */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Volume2 className="w-4 h-4" />
                TTS 设置
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-1">
                <Label className="text-xs">{t("settings.ttsProvider")}</Label>
                <Select
                  value={ttsProvider}
                  onChange={(e) => setTtsProvider(e.target.value)}
                  options={[
                    { value: "edge-tts", label: "Edge TTS (免费)" },
                    { value: "openai", label: "OpenAI TTS" },
                    { value: "azure", label: "Azure TTS" },
                    { value: "fish-audio", label: "Fish Audio" },
                    { value: "custom", label: "自定义 (Custom)" },
                  ]}
                />
              </div>

              {ttsProvider === "edge-tts" && (
                <>
                  <Separator />
                  <div className="space-y-1">
                    <Label className="text-xs">{t("settings.ttsVoice")}</Label>
                    <Select
                      value={edgeVoice}
                      onChange={(e) => setEdgeVoice(e.target.value)}
                      options={[
                        { value: "zh-CN-YunxiNeural", label: "云希（男声）" },
                        { value: "zh-CN-XiaoxiaoNeural", label: "晓晓（女声）" },
                        { value: "zh-CN-YunjianNeural", label: "云健（男声）" },
                        { value: "zh-CN-XiaoyiNeural", label: "晓伊（女声）" },
                      ]}
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">{t("settings.ttsRate")}</Label>
                    <Input type="number" value={edgeRate} onChange={(e) => setEdgeRate(e.target.value)} min={0.5} max={2.0} step={0.1} />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">{t("settings.ttsVolume")}</Label>
                    <Input type="number" value={edgeVolume} onChange={(e) => setEdgeVolume(e.target.value)} min={0.0} max={1.0} step={0.1} />
                  </div>
                </>
              )}

              {ttsProvider === "openai" && (
                <>
                  <Separator />
                  <div className="space-y-1">
                    <Label className="text-xs">{t("settings.apiKey")}</Label>
                    <Input type="password" value={openaiTtsKey} onChange={(e) => setOpenaiTtsKey(e.target.value)} placeholder={t("settings.openaiKeyPlaceholder")} />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">{t("settings.baseUrl")}</Label>
                    <Input value={openaiTtsBaseUrl} onChange={(e) => setOpenaiTtsBaseUrl(e.target.value)} />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">{t("settings.model")}</Label>
                    <Select value={openaiTtsModel} onChange={(e) => setOpenaiTtsModel(e.target.value)} options={[{ value: "tts-1", label: "tts-1" }, { value: "tts-1-hd", label: "tts-1-hd" }]} />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">{t("settings.ttsVoice")}</Label>
                    <Select value={openaiTtsVoice} onChange={(e) => setOpenaiTtsVoice(e.target.value)} options={[
                      { value: "alloy", label: "alloy" }, { value: "echo", label: "echo" }, { value: "fable", label: "fable" },
                      { value: "onyx", label: "onyx" }, { value: "nova", label: "nova" }, { value: "shimmer", label: "shimmer" },
                    ]} />
                  </div>
                </>
              )}

              {ttsProvider === "azure" && (
                <>
                  <Separator />
                  <div className="space-y-1">
                    <Label className="text-xs">{t("settings.apiKey")}</Label>
                    <Input type="password" value={azureKey} onChange={(e) => setAzureKey(e.target.value)} />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">{t("settings.region")}</Label>
                    <Input value={azureRegion} onChange={(e) => setAzureRegion(e.target.value)} placeholder="eastasia" />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">{t("settings.ttsVoice")}</Label>
                    <Select value={azureVoice} onChange={(e) => setAzureVoice(e.target.value)} options={[
                      { value: "zh-CN-YunxiNeural", label: "zh-CN-YunxiNeural" }, { value: "zh-CN-XiaoxiaoNeural", label: "zh-CN-XiaoxiaoNeural" },
                      { value: "en-US-JennyNeural", label: "en-US-JennyNeural" }, { value: "en-US-GuyNeural", label: "en-US-GuyNeural" },
                    ]} />
                  </div>
                </>
              )}

              {ttsProvider === "fish-audio" && (
                <>
                  <Separator />
                  <div className="space-y-1">
                    <Label className="text-xs">{t("settings.apiKey")}</Label>
                    <Input type="password" value={fishKey} onChange={(e) => setFishKey(e.target.value)} />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">{t("settings.baseUrl")}</Label>
                    <Input value={fishBaseUrl} onChange={(e) => setFishBaseUrl(e.target.value)} />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">{t("settings.model")}</Label>
                    <Input value={fishModel} onChange={(e) => setFishModel(e.target.value)} placeholder="可选" />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">{t("settings.ttsVoice")}</Label>
                    <Input value={fishVoice} onChange={(e) => setFishVoice(e.target.value)} placeholder="可选，留空使用默认" />
                  </div>
                </>
              )}

              {ttsProvider === "custom" && (
                <>
                  <Separator />
                  <p className="text-xs text-muted-foreground">支持任何 OpenAI 兼容的 TTS API</p>
                  <div className="space-y-1">
                    <Label className="text-xs">{t("settings.apiKey")}</Label>
                    <Input type="password" value={customTtsKey} onChange={(e) => setCustomTtsKey(e.target.value)} placeholder="TTS API Key" />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">{t("settings.baseUrl")}</Label>
                    <Input value={customTtsBaseUrl} onChange={(e) => setCustomTtsBaseUrl(e.target.value)} placeholder="https://api.example.com/v1/audio/speech" />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">{t("settings.model")}</Label>
                    <Input value={customTtsModel} onChange={(e) => setCustomTtsModel(e.target.value)} placeholder="tts-model-name" />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">{t("settings.ttsVoice")}</Label>
                    <Input value={customTtsVoice} onChange={(e) => setCustomTtsVoice(e.target.value)} placeholder="voice-name" />
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          {/* JSON Config Import/Export */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center justify-between">
                <span>配置导入/导出</span>
                <div className="flex gap-1">
                  <Button size="sm" variant="outline" className="h-7 px-2 text-xs gap-1" onClick={handleCopyConfig}>
                    <Copy className="w-3 h-3" /> 复制
                  </Button>
                  <Button size="sm" variant="outline" className="h-7 px-2 text-xs gap-1" onClick={handlePasteConfig}>
                    <ClipboardPaste className="w-3 h-3" /> 粘贴
                  </Button>
                </div>
              </CardTitle>
            </CardHeader>
            {showJsonPanel && (
              <CardContent>
                <Textarea
                  className="font-mono text-xs h-32"
                  value={jsonConfig}
                  onChange={(e) => setJsonConfig(e.target.value)}
                  placeholder='{"llm": {...}, "tts": {...}}'
                />
                <p className="text-xs text-muted-foreground mt-1">
                  粘贴 JSON 后点击"粘贴"按钮导入，或修改后点"保存"
                </p>
              </CardContent>
            )}
          </Card>
        </div>

        <div className="flex justify-end gap-2 p-4 border-t shrink-0">
          <Button variant="outline" onClick={onClose}>
            {t("settings.cancel")}
          </Button>
          <Button onClick={handleSave}>{t("settings.save")}</Button>
        </div>
      </div>
    </div>
  );
}
