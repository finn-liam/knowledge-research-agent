import { useQuery } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { api } from "@/lib/api";
import type { KbDocument } from "@/types";

/** 切片预览对话框：展示文档切分结果，验证切片质量 */
export function ChunkPreviewDialog({
  doc,
  open,
  onOpenChange,
}: {
  doc: KbDocument | null;
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const { data } = useQuery({
    queryKey: ["kb-detail", doc?.id],
    queryFn: () => api.getDocument(doc!.id),
    enabled: open && !!doc,
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="truncate pr-6">{doc?.name}</DialogTitle>
        </DialogHeader>
        <div className="text-xs text-muted-foreground">
          共 {data?.chunk_count ?? 0} 个切片 · 每个切片为一次检索的最小单元
        </div>
        <ScrollArea className="max-h-[420px] pr-2">
          <div className="space-y-2.5">
            {(data?.chunks ?? []).map((c) => (
              <div key={c.id} className="rounded-xl border bg-muted/30 p-3">
                <div className="mb-1 text-[11px] font-medium text-primary">片段 {c.chunk_index + 1}</div>
                <div className="whitespace-pre-wrap text-[13px] leading-relaxed text-foreground/85">
                  {c.text}
                </div>
              </div>
            ))}
            {data && data.chunks.length === 0 && (
              <div className="py-8 text-center text-sm text-muted-foreground">
                {data.status === "indexed" ? "暂无切片" : `文档正在${data.status}中，完成后可见切片`}
              </div>
            )}
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
