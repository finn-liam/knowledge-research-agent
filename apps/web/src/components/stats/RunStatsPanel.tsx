"use client";

import { memo, useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { formatDuration, formatNumber } from "@/lib/format";
import type { RunStats } from "@/types";

/** 相关度半环仪表：挂载后 stroke-dashoffset 从 0 滑到目标值（一次入场动画） */
function RelevanceGauge({ value }: { value: number }) {
  const [armed, setArmed] = useState(false);
  useEffect(() => {
    const id = requestAnimationFrame(() => setArmed(true));
    return () => cancelAnimationFrame(id);
  }, []);
  const clamped = Math.max(0, Math.min(100, Math.round(value)));

  return (
    <div className="relative mx-auto mt-3 w-[176px]">
      <svg viewBox="0 0 120 68" className="w-full" aria-hidden>
        <path
          d="M10 60 A50 50 0 0 1 110 60"
          pathLength={100}
          fill="none"
          strokeWidth="7"
          strokeLinecap="round"
          className="stroke-border"
        />
        <path
          d="M10 60 A50 50 0 0 1 110 60"
          pathLength={100}
          fill="none"
          strokeWidth="7"
          strokeLinecap="round"
          strokeDasharray={100}
          strokeDashoffset={armed ? 100 - clamped : 100}
          className="stroke-primary transition-[stroke-dashoffset] duration-1000 ease-out motion-reduce:transition-none"
        />
      </svg>
      <div className="pointer-events-none absolute inset-x-0 bottom-0 text-center">
        <span className="text-[26px] font-bold leading-none tabular-nums">{clamped}</span>
        <span className="ml-0.5 text-sm font-semibold text-muted-foreground">%</span>
        <div className="mt-1.5 text-[11px] font-medium text-muted-foreground">平均相关度</div>
      </div>
    </div>
  );
}

/** 研究页右侧「Research Statistics」运行统计：相关度仪表 + 耗时/信息源/命中文档三列 */
function RunStatsPanelInner({ stats }: { stats: Partial<RunStats> }) {
  const cells = [
    { label: "耗时", value: formatDuration(stats.duration_sec ?? 0) },
    { label: "信息源", value: `${stats.sources_count ?? 0} 个` },
    { label: "命中文档", value: `${formatNumber(stats.docs_processed ?? 0)} 篇` },
  ];

  return (
    <Card>
      <CardContent className="p-4">
        <div className="text-sm font-semibold">Research Statistics</div>
        <RelevanceGauge value={stats.relevance_avg ?? 0} />
        <div className="mt-4 grid grid-cols-3 divide-x divide-border/60 rounded-xl border bg-muted/30 py-2.5">
          {cells.map(({ label, value }) => (
            <div key={label} className="px-2 text-center">
              <div className="text-sm font-semibold tabular-nums">{value}</div>
              <div className="mt-0.5 text-[11px] text-muted-foreground">{label}</div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

/** memo */
export const RunStatsPanel = memo(RunStatsPanelInner);
