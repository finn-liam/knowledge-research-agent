import type { LucideIcon } from "lucide-react";

/** 统计行：图标 + 标签 + 值（首页/研究页两面板复用） */
export function StatRow({
  icon: Icon,
  label,
  value,
}: {
  icon: LucideIcon;
  label: string;
  value: string | number;
}) {
  return (
    <div className="flex min-w-0 items-center gap-3 py-2">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-muted">
        <Icon className="h-4 w-4 text-muted-foreground" />
      </div>
      <div className="min-w-0 flex-1 truncate text-sm text-muted-foreground">{label}</div>
      <div className="shrink-0 whitespace-nowrap text-sm font-semibold tabular-nums">{value}</div>
    </div>
  );
}
