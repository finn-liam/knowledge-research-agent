import { Clock3, Database, FileCheck2, Target } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { formatDuration, formatNumber } from "@/lib/format";
import type { RunStats } from "@/types";
import { StatRow } from "./StatRow";

/** 研究页右侧「Research Statistics」运行统计：查询时间/信息源/处理文档/相关度评分 */
export function RunStatsPanel({ stats }: { stats: Partial<RunStats> }) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="text-sm font-semibold">Research Statistics</div>
        <div className="mt-2 divide-y divide-border/60">
          <StatRow icon={Clock3} label="查询时间" value={formatDuration(stats.duration_sec ?? 0)} />
          <StatRow icon={Database} label="信息源" value={`${stats.sources_count ?? 0} 个`} />
          <StatRow icon={FileCheck2} label="命中文档" value={`${formatNumber(stats.docs_processed ?? 0)} 篇`} />
          <StatRow icon={Target} label="相关度评分" value={`${stats.relevance_avg ?? 0}%`} />
        </div>
      </CardContent>
    </Card>
  );
}
