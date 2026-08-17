import { formatNumber } from "@/lib/format";
import type { SourceType } from "@/types";
import { SourceTypeIcon } from "./SourceTypeIcon";

/** 首页 Sources 统计的单行：图标 + 类型名 + 数量 */
export function SourceStatRow({
  type,
  label,
  count,
}: {
  type: SourceType;
  label: string;
  count: number;
}) {
  return (
    <div className="flex min-w-0 items-center gap-3 py-2">
      <SourceTypeIcon type={type} />
      <div className="min-w-0 flex-1 truncate text-sm text-foreground/90">{label}</div>
      <div className="shrink-0 whitespace-nowrap text-sm font-medium tabular-nums text-foreground/80">
        {formatNumber(count)}
      </div>
    </div>
  );
}
