"use client";

import { useCountUp } from "@/hooks/use-count-up";
import { formatNumber } from "@/lib/format";
import type { SourceType } from "@/types";
import { SourceTypeIcon } from "./SourceTypeIcon";

/** 首页 Sources 统计单行：语义色图标（类型编码）+ 类型名 + 大号等宽计数（进视口滚动） */
export function SourceStatRow({
  type,
  label,
  count,
}: {
  type: SourceType;
  label: string;
  count: number;
}) {
  const { ref, value } = useCountUp(count);
  return (
    <div ref={ref} className="flex min-w-0 items-center gap-3 py-2.5">
      <SourceTypeIcon type={type} />
      <div className="min-w-0 flex-1 truncate text-sm text-foreground/80">{label}</div>
      <div className="shrink-0 whitespace-nowrap text-[22px] font-semibold leading-none tabular-nums">
        {formatNumber(value)}
      </div>
    </div>
  );
}
