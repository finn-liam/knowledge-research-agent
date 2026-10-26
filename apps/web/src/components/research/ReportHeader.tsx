"use client";

import { memo } from "react";
import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

/** 研究页标题栏：报告标题 + 导出（分享/更多在功能上线前不渲染，避免死按钮） */
function ReportHeaderInner({
  title,
  taskId,
  canExport,
}: {
  title: string;
  taskId: string | null;
  canExport: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-3 border-b bg-background/95 px-4 py-3 md:px-6">
      <h1 className="truncate text-[15px] font-semibold" title={title || "研究报告"}>
        {title || "研究报告"}
      </h1>
      <Button
        variant="outline"
        size="sm"
        className="h-8 shrink-0 gap-1.5 text-xs"
        disabled={!canExport || !taskId}
        onClick={() => taskId && window.open(api.exportUrl(taskId), "_blank")}
      >
        <Download className="h-3.5 w-3.5" />
        导出报告
      </Button>
    </div>
  );
}

/** memo：标题栏不随流式 token 变化重渲染 */
export const ReportHeader = memo(ReportHeaderInner);
