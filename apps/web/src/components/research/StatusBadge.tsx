import type { RunPhase } from "@/features/research/researchStore";

/** Agent 工作状态徽章：处理中(脉冲点)/已完成/失败/已中断（术语与步骤卡一致） */
export function StatusBadge({ phase }: { phase: RunPhase }) {
  if (phase === "streaming") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-accent px-2.5 py-0.5 text-xs font-medium text-accent-foreground">
        <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-primary" />
        处理中
      </span>
    );
  }
  if (phase === "done") {
    return (
      <span className="inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-600">
        已完成
      </span>
    );
  }
  if (phase === "failed") {
    return (
      <span className="inline-flex items-center rounded-full bg-rose-50 px-2.5 py-0.5 text-xs font-medium text-rose-600">
        失败
      </span>
    );
  }
  if (phase === "interrupted") {
    return (
      <span className="inline-flex items-center rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-600">
        已中断
      </span>
    );
  }
  return null;
}
