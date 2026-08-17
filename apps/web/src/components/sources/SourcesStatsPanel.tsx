import { Card, CardContent } from "@/components/ui/card";
import type { SourceStatItem, SourceType } from "@/types";
import { SourceStatRow } from "./SourceStatRow";

/** 首页右侧「Sources」分类统计面板 */
export function SourcesStatsPanel({ items }: { items: SourceStatItem[] }) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="text-sm font-semibold">Sources</div>
          <button className="text-xs font-medium text-primary hover:underline">View all</button>
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
