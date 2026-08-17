import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

const STATUS_MAP: Record<string, { text: string; variant: "secondary" | "default" | "destructive" | "muted" }> = {
  pending: { text: "等待中", variant: "muted" },
  parsing: { text: "解析中", variant: "default" },
  embedding: { text: "向量化中", variant: "default" },
  indexed: { text: "已索引", variant: "secondary" },
  failed: { text: "失败", variant: "destructive" },
};

/** 文档摄入状态徽标（失败时悬停显示错误原因） */
export function DocumentStatusBadge({ status, error }: { status: string; error?: string }) {
  const meta = STATUS_MAP[status] ?? STATUS_MAP.pending;
  const badge = (
    <Badge variant={meta.variant} className={status === "embedding" || status === "parsing" ? "animate-pulse-soft" : ""}>
      {meta.text}
    </Badge>
  );
  if (status === "failed" && error) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>{badge}</TooltipTrigger>
        <TooltipContent>{error}</TooltipContent>
      </Tooltip>
    );
  }
  return badge;
}
