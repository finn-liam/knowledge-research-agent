import { useQuery } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { formatRelevance } from "@/lib/format";
import type { SourceItem } from "@/types";
import { parseKbUrl } from "./SourceItemCard";

/** 完整片段弹窗：展示知识库来源的片段全文（AI 论断可完整溯源核对） */
export function ChunkViewerDialog({
  source,
  open,
  onOpenChange,
}: {
  source: SourceItem | null;
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const kbLoc = source ? parseKbUrl(source.url) : null;
  const { data, isLoading } = useQuery({
    queryKey: ["kb-chunk", kbLoc?.documentId, kbLoc?.chunkIndex],
    queryFn: () => api.kbChunk(kbLoc!.documentId, kbLoc!.chunkIndex),
    enabled: open && !!kbLoc,
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 pr-6 text-sm">
            <span className="font-semibold text-primary">[{source?.ref_no ?? ""}]</span>
            <span className="truncate">{data?.document_name ?? source?.title ?? ""}</span>
          </DialogTitle>
          <DialogDescription className="flex items-center gap-2">
            {data && <span>片段 {data.chunk_index + 1}</span>}
            {source && (
              <>
                <Badge variant="muted" className="px-1.5 text-[11px] font-normal">
                  {source.source_label || source.type}
                </Badge>
                <span>相关度 {formatRelevance(source.relevance)}</span>
              </>
            )}
          </DialogDescription>
        </DialogHeader>
        <ScrollArea className="max-h-[420px] pr-2">
          {isLoading ? (
            <div className="flex items-center justify-center gap-2 py-10 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> 加载片段全文...
            </div>
          ) : (
            <div className="whitespace-pre-wrap rounded-xl bg-muted/40 p-4 text-[13px] leading-relaxed text-foreground/90">
              {data?.text ?? "片段内容加载失败"}
            </div>
          )}
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
