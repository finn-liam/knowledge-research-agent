import { Info } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { SourceStatItem, SourceType } from "@/types";
import { SourceStatRow } from "./SourceStatRow";

/** 首页右侧「Sources」分类统计面板（累计口径） */
export function SourcesStatsPanel({ items }: { items: SourceStatItem[] }) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex min-w-0 items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-1.5 text-sm font-semibold">
            <span className="truncate">Sources</span>
            <Tooltip>
              <TooltipTrigger asChild>
                <span className="shrink-0 cursor-help">
                  <Info className="h-3.5 w-3.5 text-muted-foreground/70" />
                </span>
              </TooltipTrigger>
              <TooltipContent className="max-w-[260px]">
                统计自历史所有研究**真实检索到**的来源片段，按类型聚合计数：企业内部文档、学术论文、网页资源。每次研究完成后自动增长。
              </TooltipContent>
            </Tooltip>
          </div>
          <button className="shrink-0 whitespace-nowrap text-xs font-medium text-primary hover:underline">
            View all
          </button>
        </div>
        <div className="mt-2 divide-y divide-border/60">
          {items.map((item) => (
            <SourceStatRow
              key={item.category}
              type={item.category as SourceType}
              label={item.label}
              count={item.count}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
