import { BookCheck, Database, FileCheck2, Target } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { formatNumber } from "@/lib/format";
import type { AnalyticsSummary } from "@/types";
import { StatRow } from "./StatRow";

/** 首页右侧「Research Statistics」全局统计面板 */
export function ResearchStatsPanel({ summary }: { summary: AnalyticsSummary | undefined }) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="text-sm font-semibold">Research Statistics</div>
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
