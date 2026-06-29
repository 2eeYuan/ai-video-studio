import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, Clock, Camera, Volume2, Move } from "lucide-react";
import type { AgentShot } from "@/lib/api";

interface StoryboardViewerProps {
  shots: AgentShot[];
  totalDuration?: number;
  onConfirm: () => void;
  loading?: boolean;
}

export function StoryboardViewer({ shots, totalDuration, onConfirm, loading }: StoryboardViewerProps) {
  const { t } = useTranslation();

  const shotTypeColors: Record<string, string> = {
    "特写": "bg-red-100 text-red-700",
    "近景": "bg-orange-100 text-orange-700",
    "中景": "bg-blue-100 text-blue-700",
    "全景": "bg-green-100 text-green-700",
    "远景": "bg-purple-100 text-purple-700",
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="text-sm text-muted-foreground">
          分镜表 · {shots.length} 个镜头
          {totalDuration && ` · 总时长 ${totalDuration}s`}
        </div>
        <Button size="sm" onClick={onConfirm} disabled={loading}>
          {loading ? (
            <span className="flex items-center gap-1">
              <span className="animate-spin">⏳</span> 生成中...
            </span>
          ) : (
            <>
              <CheckCircle2 className="w-3 h-3 mr-1" />
              确认分镜，开始生成视频
            </>
          )}
        </Button>
      </div>

      <div className="border rounded-lg overflow-hidden">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-muted/50 text-left">
              <th className="px-3 py-2 font-medium">镜头</th>
              <th className="px-3 py-2 font-medium">景别</th>
              <th className="px-3 py-2 font-medium">角度</th>
              <th className="px-3 py-2 font-medium">画面描述</th>
              <th className="px-3 py-2 font-medium">声音</th>
              <th className="px-3 py-2 font-medium">运镜</th>
              <th className="px-3 py-2 font-medium text-right">时长</th>
            </tr>
          </thead>
          <tbody>
            {shots.map((shot, i) => (
              <tr key={i} className="border-t hover:bg-muted/30 transition-colors">
                <td className="px-3 py-2 font-mono text-xs text-muted-foreground">
                  {shot.shot_id}
                </td>
                <td className="px-3 py-2">
                  <Badge
                    variant="secondary"
                    className={`text-[10px] ${shotTypeColors[shot.shot_type] || ""}`}
                  >
                    {shot.shot_type}
                  </Badge>
                </td>
                <td className="px-3 py-2 text-muted-foreground">{shot.angle}</td>
                <td className="px-3 py-2 max-w-[300px]">
                  <div className="line-clamp-2">{shot.description}</div>
                  {shot.narration_segment && (
                    <div className="text-muted-foreground mt-1 italic text-[10px]">
                      旁白：{shot.narration_segment}
                    </div>
                  )}
                </td>
                <td className="px-3 py-2 text-muted-foreground max-w-[120px] truncate">
                  {shot.sound}
                </td>
                <td className="px-3 py-2">
                  <div className="flex items-center gap-1 text-muted-foreground">
                    <Move className="w-3 h-3" />
                    {shot.camera_movement}
                  </div>
                </td>
                <td className="px-3 py-2 text-right">
                  <div className="flex items-center justify-end gap-1 text-muted-foreground">
                    <Clock className="w-3 h-3" />
                    {shot.duration}s
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
