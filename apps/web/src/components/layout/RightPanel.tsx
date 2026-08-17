import type { ReactNode } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";

/** 右侧面板容器：固定宽度、独立滚动（首页/研究页注入不同面板组合） */
export function RightPanel({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <aside className={cn("w-[336px] shrink-0 border-l bg-background", className)}>
      <ScrollArea className="h-full w-full">
        <div className="min-w-0 space-y-4 p-4">{children}</div>
      </ScrollArea>
    </aside>
  );
}
