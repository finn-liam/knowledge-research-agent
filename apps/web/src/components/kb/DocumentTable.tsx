import { Eye, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { relativeTime } from "@/lib/format";
import type { KbDocument } from "@/types";
import { DocumentStatusBadge } from "./DocumentStatusBadge";

/** 文档管理表格：名称/类型/大小/状态/切片/时间/操作 */
export function DocumentTable({
  documents,
  onPreview,
  onDelete,
}: {
  documents: KbDocument[];
  onPreview: (doc: KbDocument) => void;
  onDelete: (doc: KbDocument) => void;
}) {
  return (
    <div className="overflow-hidden rounded-xl border bg-card">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/50 text-left text-xs text-muted-foreground">
            <th className="px-4 py-2.5 font-medium">文档名称</th>
            <th className="w-20 px-3 py-2.5 font-medium">类型</th>
            <th className="w-24 px-3 py-2.5 font-medium">大小</th>
            <th className="w-24 px-3 py-2.5 font-medium">状态</th>
            <th className="w-20 px-3 py-2.5 text-right font-medium">切片</th>
            <th className="w-28 px-3 py-2.5 font-medium">上传时间</th>
            <th className="w-24 px-3 py-2.5 text-right font-medium">操作</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border/60">
          {documents.map((d) => (
            <tr key={d.id} className="transition-colors hover:bg-accent/30">
              <td className="max-w-[320px] truncate px-4 py-2.5 font-medium" title={d.name}>
                {d.name}
              </td>
              <td className="px-3 py-2.5">
                <span className="rounded-md bg-muted px-1.5 py-0.5 text-xs uppercase text-muted-foreground">
                  {d.doc_type}
                </span>
              </td>
              <td className="px-3 py-2.5 text-muted-foreground">
                {d.size_bytes > 1024 * 1024
                  ? `${(d.size_bytes / 1024 / 1024).toFixed(1)} MB`
                  : `${Math.max(1, Math.round(d.size_bytes / 1024))} KB`}
              </td>
              <td className="px-3 py-2.5">
                <DocumentStatusBadge status={d.status} error={d.error_msg} />
              </td>
              <td className="px-3 py-2.5 text-right tabular-nums">{d.chunk_count}</td>
              <td className="px-3 py-2.5 text-xs text-muted-foreground">
                {relativeTime(d.created_at)}
              </td>
              <td className="px-3 py-2.5">
                <div className="flex justify-end gap-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 text-muted-foreground"
                    title="预览切片"
                    onClick={() => onPreview(d)}
                  >
                    <Eye className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 text-muted-foreground hover:text-rose-600"
                    title="删除"
                    onClick={() => onDelete(d)}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </td>
            </tr>
          ))}
          {documents.length === 0 && (
            <tr>
              <td colSpan={7} className="px-4 py-12 text-center text-sm text-muted-foreground">
                知识库为空，上传第一批文档开始构建企业检索资产
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
