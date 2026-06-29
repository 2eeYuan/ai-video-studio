import { useTranslation } from "react-i18next";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Loader2 } from "lucide-react";
import type { AgentDirection } from "@/lib/api";

interface DirectionSelectorProps {
  directions: AgentDirection[];
  onSelect: (directionId: number) => void;
  loading?: boolean;
}

export function DirectionSelector({ directions, onSelect, loading }: DirectionSelectorProps) {
  const { t } = useTranslation();

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground mr-2" />
        <span className="text-sm text-muted-foreground">AI 正在构思创意方向...</span>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="text-sm text-muted-foreground mb-4">
        请选择一个创意方向，AI 将根据你的选择生成剧本：
      </div>
      <div className="grid grid-cols-2 gap-3">
        {directions.map((d) => (
          <Card
            key={d.id}
            className="cursor-pointer hover:border-primary hover:shadow-md transition-all group"
            onClick={() => onSelect(d.id)}
          >
            <CardContent className="p-4 space-y-2">
              <div className="flex items-center gap-2">
                <Badge variant="secondary" className="text-xs">
                  {d.label}
                </Badge>
              </div>
              <h4 className="text-sm font-medium leading-tight">{d.concept}</h4>
              <p className="text-xs text-muted-foreground leading-relaxed">
                {d.description}
              </p>
              <div className="text-xs text-primary opacity-0 group-hover:opacity-100 transition-opacity pt-1">
                点击选择此方向 →
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
