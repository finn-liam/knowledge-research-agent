import { BookCheck, Database, FileCheck2, Info, Target } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { formatNumber } from "@/lib/format";
import type { AnalyticsSummary } from "@/types";
import { StatRow } from "./StatRow";

/** 首页右侧「Research Statistics」全局统计面板（累计口径） */
export function ResearchStatsPanel({ summary }: { summary: AnalyticsSummary | undefined }) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center gap-1.5 text-sm font-semibold">
          Research Statistics
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="cursor-help">
                <Info className="h-3.5 w-3.5 text-muted-foreground/70" />
              </span>
            </TooltipTrigger>
            <TooltipContent className="max-w-[280px]">
              累计统计：Total Research=历史研究总次数；Knowledge Sources=累计检索来源数；
              Documents Hit=累计命中文档数；Accuracy Rate=历史平均相关度。
            </TooltipContent>
          </Tooltip>
        </div>
        <div className="mt-2 divide-y divide-border/60">
          <StatRow icon={BookCheck} label="Total Research" value={summary?.total_research ?? 0} />
          <StatRow
            icon={Database}
            label="Knowledge Sources"
            value={formatNumber(summary?.knowledge_sources ?? 0)}
          />
          <StatRow
            icon={FileCheck2}
            label="Documents Hit"
            value={formatNumber(summary?.documents_processed ?? 0)}
          />
          <StatRow icon={Target} label="Accuracy Rate" value={`${summary?.accuracy_rate ?? 0}%`} />
        </div>
      </CardContent>
    </Card>
  );
}
