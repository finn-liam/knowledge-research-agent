import { memo } from "react";
import { Download, MoreHorizontal, Share2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

/** 研究页标题栏：报告标题 + 分享/导出/更多 */
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
    <div className="flex items-center justify-between border-b bg-background/95 px-6 py-3">
      <h1 className="truncate text-[15px] font-semibold">{title || "研究报告"}</h1>
      <div className="flex items-center gap-1">
        <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground">
          <Share2 className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 text-muted-foreground"
          disabled={!canExport || !taskId}
          onClick={() => taskId && window.open(api.exportUrl(taskId), "_blank")}
        >
          <Download className="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground">
          <MoreHorizontal className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

/** memo：标题栏不随流式 token 变化重渲染 */
export const ReportHeader = memo(ReportHeaderInner);
