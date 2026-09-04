"use client";

import { memo, useEffect, useRef } from "react";
import {
  AlertCircle,
  CheckCircle2,
  FileCheck2,
  Gauge,
  Layers,
  RefreshCw,
  Route,
  SkipForward,
  XCircle,
  type LucideIcon,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { useResearchStore } from "@/features/research/researchStore";
import { cn } from "@/lib/utils";
import type { TimelineEntry, TimelineKind } from "@/types";

const KIND_META: Record<TimelineKind, { icon: LucideIcon; cls: string }> = {
  router: { icon: Route, cls: "bg-violet-50 text-violet-600" },
  step_started: { icon: Gauge, cls: "bg-accent text-primary" },
  step_completed: { icon: CheckCircle2, cls: "bg-emerald-50 text-emerald-600" },
  step_failed: { icon: XCircle, cls: "bg-rose-50 text-rose-600" },
  step_skipped: { icon: SkipForward, cls: "bg-sky-50 text-sky-600/80" },
  sources: { icon: Layers, cls: "bg-blue-50 text-blue-600" },
  grade: { icon: Gauge, cls: "bg-amber-50 text-amber-600" },
  rewrite: { icon: RefreshCw, cls: "bg-orange-50 text-orange-600" },
  report_done: { icon: FileCheck2, cls: "bg-emerald-50 text-emerald-600" },
  error: { icon: AlertCircle, cls: "bg-rose-50 text-rose-600" },
};

function fmtTime(ts: number): string {
  return new Date(ts).toLocaleTimeString("zh-CN", { hour12: false });
}

function TimelineRow({ entry }: { entry: TimelineEntry }) {
  const meta = KIND_META[entry.kind] ?? KIND_META.router;
  const Icon = meta.icon;
  return (
    <div className="flex items-start gap-2.5 py-1.5">
      <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md">
        <Icon className={cn("h-3.5 w-3.5", meta.cls.split(" ")[1])} />
      </div>
      <div className="min-w-0 flex-1 text-[12.5px] leading-relaxed text-foreground/80">
        {entry.text}
      </div>
      <div className="shrink-0 pt-0.5 font-mono text-[11px] tabular-nums text-muted-foreground/70">
        {fmtTime(entry.ts)}
      </div>
    </div>
  );
}

/** 研究过程时间线（C1）：把 SSE 事件渲染成 Agent 思考直播，零后端改动 */
function ProcessTimelineInner() {
  const timeline = useResearchStore((s) => s.timeline);
  const streaming = useResearchStore((s) => s.phase === "streaming");

  // 流式期间自动滚到最新条目
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (streaming && timeline.length) {
      endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [timeline.length, streaming]);

  if (!timeline.length) return null;

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="text-sm font-semibold">研究过程</div>
          <span className="text-[11px] text-muted-foreground">{timeline.length} 条事件</span>
        </div>
        <div className="relative mt-2 max-h-[240px] overflow-y-auto pr-1">
          {/* 左侧竖线连接事件流 */}
          <div className="absolute bottom-2 left-[11px] top-2 w-px bg-border/70" aria-hidden />
          <div className="relative">
            {timeline.map((entry) => (
              <TimelineRow key={entry.id} entry={entry} />
            ))}
            <div ref={endRef} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

/** memo：时间线自身变化才重渲染，不随 reportBuffer 每 100ms 刷 */
export const ProcessTimeline = memo(ProcessTimelineInner);
