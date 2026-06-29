import { useTranslation } from "react-i18next";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Type, Music } from "lucide-react";
import type { SubtitleConfig, BgmConfig } from "./WorkspaceLayout";

interface SubtitlePanelProps {
  subtitleConfig: SubtitleConfig;
  onSubtitleConfigChange: (config: SubtitleConfig) => void;
  bgmConfig: BgmConfig;
  onBgmConfigChange: (config: BgmConfig) => void;
}

export function SubtitlePanel({ subtitleConfig, onSubtitleConfigChange, bgmConfig, onBgmConfigChange }: SubtitlePanelProps) {
  const { t } = useTranslation();

  const updateSubtitle = (partial: Partial<SubtitleConfig>) =>
    onSubtitleConfigChange({ ...subtitleConfig, ...partial });

  const updateBgm = (partial: Partial<BgmConfig>) =>
    onBgmConfigChange({ ...bgmConfig, ...partial });

  return (
    <div className="flex flex-col h-full overflow-y-auto p-3 gap-3">
      {/* Subtitle Settings */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Type className="w-4 h-4" />
            {t("workspace.subtitle")}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between">
            <Label className="text-xs">{t("subtitle.enable")}</Label>
            <input
              type="checkbox"
              checked={subtitleConfig.enabled}
              onChange={(e) => updateSubtitle({ enabled: e.target.checked })}
              className="rounded"
            />
          </div>
          {subtitleConfig.enabled && (
            <>
              <div className="space-y-1">
                <Label className="text-xs">{t("subtitle.font")}</Label>
                <Select
                  value={subtitleConfig.font}
                  onChange={(e) => updateSubtitle({ font: e.target.value })}
                  options={[
                    { value: "MicrosoftYaHeiBold.ttc", label: "微软雅黑 粗体" },
                    { value: "MicrosoftYaHeiNormal.ttc", label: "微软雅黑 常规" },
                    { value: "STHeitiMedium.ttc", label: "黑体-中" },
                  ]}
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">{t("subtitle.position")}</Label>
                <Select
                  value={subtitleConfig.position}
                  onChange={(e) => updateSubtitle({ position: e.target.value })}
                  options={[
                    { value: "top", label: t("subtitle.top") },
                    { value: "center", label: t("subtitle.center") },
                    { value: "bottom", label: t("subtitle.bottom") },
                  ]}
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1">
                  <Label className="text-xs">{t("subtitle.fontSize")}</Label>
                  <Input
                    type="number"
                    value={subtitleConfig.fontSize}
                    onChange={(e) => updateSubtitle({ fontSize: Number(e.target.value) })}
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">{t("subtitle.strokeWidth")}</Label>
                  <Input
                    type="number"
                    value={subtitleConfig.strokeWidth}
                    step={0.1}
                    onChange={(e) => updateSubtitle({ strokeWidth: Number(e.target.value) })}
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1">
                  <Label className="text-xs">{t("subtitle.fontColor")}</Label>
                  <div className="flex items-center gap-2">
                    <input
                      type="color"
                      value={subtitleConfig.fontColor}
                      onChange={(e) => updateSubtitle({ fontColor: e.target.value })}
                      className="w-8 h-8 rounded cursor-pointer"
                    />
                    <span className="text-xs text-muted-foreground">{subtitleConfig.fontColor}</span>
                  </div>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">{t("subtitle.strokeColor")}</Label>
                  <div className="flex items-center gap-2">
                    <input
                      type="color"
                      value={subtitleConfig.strokeColor}
                      onChange={(e) => updateSubtitle({ strokeColor: e.target.value })}
                      className="w-8 h-8 rounded cursor-pointer"
                    />
                    <span className="text-xs text-muted-foreground">{subtitleConfig.strokeColor}</span>
                  </div>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <Label className="text-xs">{t("subtitle.bgEnable")}</Label>
                <input
                  type="checkbox"
                  checked={subtitleConfig.bgEnabled}
                  onChange={(e) => updateSubtitle({ bgEnabled: e.target.checked })}
                  className="rounded"
                />
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <Separator />

      {/* Audio Settings */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Music className="w-4 h-4" />
            {t("audio.bgm")}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="space-y-1">
            <Label className="text-xs">{t("audio.bgm")}</Label>
            <Select
              value={bgmConfig.type}
              onChange={(e) => updateBgm({ type: e.target.value })}
              options={[
                { value: "random", label: t("audio.randomBgm") },
                { value: "", label: t("audio.noBgm") },
                { value: "custom", label: t("audio.customBgm") },
              ]}
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">{t("audio.bgmVolume")}</Label>
            <input
              type="range"
              min={0}
              max={1}
              step={0.1}
              value={bgmConfig.volume}
              onChange={(e) => updateBgm({ volume: Number(e.target.value) })}
              className="w-full"
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">{t("audio.rate")}</Label>
            <Select
              value={String(bgmConfig.rate)}
              onChange={(e) => updateBgm({ rate: Number(e.target.value) })}
              options={[0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.5].map((n) => ({
                value: String(n),
                label: `${n}x`,
              }))}
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
