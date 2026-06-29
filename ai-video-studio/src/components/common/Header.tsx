import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Monitor, Sun, Moon, Settings, Film } from "lucide-react";

interface HeaderProps {
  projectName?: string;
  status?: string;
  onSettings?: () => void;
}

export function Header({ projectName, status = "draft", onSettings }: HeaderProps) {
  const { t } = useTranslation();
  const isDark = document.documentElement.classList.contains("dark");

  const toggleTheme = () => {
    document.documentElement.classList.toggle("dark");
  };

  const statusColors: Record<string, string> = {
    draft: "bg-secondary",
    generating: "bg-amber-500 animate-pulse",
    done: "bg-green-500",
    failed: "bg-destructive",
  };

  return (
    <header
      className="flex items-center justify-between h-12 px-4 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60"
      data-tauri-drag-region
    >
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <Film className="w-5 h-5 text-primary" />
          <span className="font-semibold text-sm">{t("app.title")}</span>
        </div>
        {projectName && (
          <>
            <span className="text-muted-foreground">/</span>
            <span className="text-sm font-medium">{projectName}</span>
            <Badge className={`${statusColors[status]} text-white text-[10px] px-1.5 py-0`}>
              {status}
            </Badge>
          </>
        )}
      </div>
      <div className="flex items-center gap-1">
        <Button variant="ghost" size="icon" onClick={toggleTheme}>
          {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </Button>
        <Button variant="ghost" size="icon" onClick={onSettings}>
          <Settings className="w-4 h-4" />
        </Button>
      </div>
    </header>
  );
}
