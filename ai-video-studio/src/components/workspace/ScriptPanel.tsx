import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select } from "@/components/ui/select";
import { Sparkles, FileText, Tags, Loader2 } from "lucide-react";
import { sidecarApi } from "@/lib/api";

interface ScriptPanelProps {
  subject: string;
  onSubjectChange: (v: string) => void;
  script: string;
  onScriptChange: (v: string) => void;
  keywords: string;
  onKeywordsChange: (v: string) => void;
}

export function ScriptPanel({
  subject, onSubjectChange,
  script, onScriptChange,
  keywords, onKeywordsChange,
}: ScriptPanelProps) {
  const { t } = useTranslation();
  const [language, setLanguage] = useState("zh-CN");
  const [isGenerating, setIsGenerating] = useState(false);
  const [isGeneratingTerms, setIsGeneratingTerms] = useState(false);

  const handleGenerateScript = async () => {
    if (!subject) return;
    setIsGenerating(true);
    try {
      const resp = await sidecarApi.generateScript(subject, language, 6, "");
      onScriptChange(resp.script);
      if (resp.keywords.length > 0) {
        onKeywordsChange(resp.keywords.join(", "));
      }
    } catch (err) {
      console.error("Script generation failed:", err);
      // Show error toast
    } finally {
      setIsGenerating(false);
    }
  };

  const handleGenerateTerms = async () => {
    if (!script) return;
    setIsGeneratingTerms(true);
    try {
      const terms = await sidecarApi.generateTerms(subject, script);
      onKeywordsChange(terms.join(", "));
    } catch (err) {
      console.error("Terms generation failed:", err);
    } finally {
      setIsGeneratingTerms(false);
    }
  };

  return (
    <div className="flex flex-col h-full overflow-y-auto p-3 gap-3">
      {/* Subject */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <FileText className="w-4 h-4" />
            {t("script.subject")}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <Input
            value={subject}
            onChange={(e) => onSubjectChange(e.target.value)}
            placeholder={t("script.subjectPlaceholder")}
          />
          <Select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            options={[
              { value: "zh-CN", label: "中文" },
              { value: "en-US", label: "English" },
              { value: "ja-JP", label: "日本語" },
            ]}
          />
        </CardContent>
      </Card>

      {/* Script */}
      <Card className="flex-1">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center justify-between">
            <span className="flex items-center gap-2">
              <Sparkles className="w-4 h-4" />
              {t("workspace.script")}
            </span>
            <Button size="sm" onClick={handleGenerateScript} disabled={isGenerating || !subject}>
              {isGenerating ? (
                <Loader2 className="w-3 h-3 mr-1 animate-spin" />
              ) : (
                <Sparkles className="w-3 h-3 mr-1" />
              )}
              {isGenerating ? t("script.generating") : t("script.generateScript")}
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Textarea
            value={script}
            onChange={(e) => onScriptChange(e.target.value)}
            placeholder={t("script.contentPlaceholder")}
            className="min-h-[200px] resize-none"
          />
        </CardContent>
      </Card>

      {/* Keywords */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center justify-between">
            <span className="flex items-center gap-2">
              <Tags className="w-4 h-4" />
              {t("script.keywords")}
            </span>
            <Button
              size="sm"
              variant="outline"
              onClick={handleGenerateTerms}
              disabled={isGeneratingTerms || !script}
            >
              {isGeneratingTerms ? (
                <Loader2 className="w-3 h-3 mr-1 animate-spin" />
              ) : null}
              {t("script.generateKeywords")}
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Input
            value={keywords}
            onChange={(e) => onKeywordsChange(e.target.value)}
            placeholder={t("script.keywordsPlaceholder")}
          />
        </CardContent>
      </Card>
    </div>
  );
}
