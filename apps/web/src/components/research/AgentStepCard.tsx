import {
  CheckCircle2,
  CircleDashed,
  Database,
  FileBarChart,
  Globe,
  GraduationCap,
  Loader2,
  Network,
  PauseCircle,
  XCircle,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { StepInfo } from "@/types";

const STEP_ICONS: Record<string, LucideIcon> = {
  kb_search: Database,
  paper_search: GraduationCap,
  web_search: Globe,
  graph_build: Network,
  report_write: FileBarChart,
};

/** 单张 Agent 步骤卡片：图标 + 名称 + 状态（已完成/处理中/等待中/已暂停） */
export function AgentStepCard({ step }: { step: StepInfo }) {
  const Icon = STEP_ICONS[step.step_key] ?? Database;
  const paused = step.status === "paused";
  return (
    <div
      className={cn(
        "flex w-[132px] flex-col gap-2 rounded-xl border bg-card p-3 transition-all animate-fade-in",
        step.status === "running" && "border-primary/50 shadow-sm",
        paused && "opacity-55",
      )}
    >
      <div
        className={cn(
          "flex h-8 w-8 items-center justify-center rounded-lg",
          step.status === "running" ? "bg-accent" : "bg-muted",
        )}
      >
        <Icon
          className={cn(
            "h-4 w-4",
            step.status === "running" ? "text-primary" : "text-muted-foreground",
          )}
        />
      </div>
      <div className="text-[12.5px] font-medium leading-tight text-foreground/90">{step.label}</div>
      <div className="flex items-center gap-1 text-[11px]">
        {step.status === "done" && (
          <>
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
            <span className="text-emerald-600">已完成</span>
          </>
        )}
        {step.status === "running" && (
          <>
            <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
            <span className="text-primary">处理中</span>
          </>
        )}
        {step.status === "pending" && (
          <>
            <CircleDashed className="h-3.5 w-3.5 text-muted-foreground/60" />
            <span className="text-muted-foreground">等待中</span>
          </>
        )}
        {step.status === "failed" && (
          <>
            <XCircle className="h-3.5 w-3.5 text-rose-500" />
            <span className="text-rose-600">失败</span>
          </>
        )}
        {step.status === "paused" && (
          <>
            <PauseCircle className="h-3.5 w-3.5 text-muted-foreground/50" />
            <span className="text-muted-foreground/70">已暂停</span>
          </>
        )}
      </div>
    </div>
  );
}
