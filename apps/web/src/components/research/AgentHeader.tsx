import { Bot, ChevronDown } from "lucide-react";
import type { RunPhase } from "@/features/research/researchStore";
import { StatusBadge } from "./StatusBadge";

/** Agent 回复头：机器人头像 + 名称 + 工作状态徽章 */
export function AgentHeader({ phase }: { phase: RunPhase }) {
  return (
    <div className="flex items-center gap-2.5">
      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-accent">
        <Bot className="h-4.5 w-4.5 text-primary" />
      </div>
      <span className="text-sm font-semibold">Knowledge Research Agent</span>
      <StatusBadge phase={phase} />
      <ChevronDown className="h-4 w-4 text-muted-foreground" />
    </div>
  );
}
