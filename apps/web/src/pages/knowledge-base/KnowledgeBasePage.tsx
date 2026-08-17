import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Clock3, FileWarning, Layers, Loader2, XCircle } from "lucide-react";
import { useState } from "react";
import { ChunkPreviewDialog } from "@/components/kb/ChunkPreviewDialog";
import { DocumentTable } from "@/components/kb/DocumentTable";
import { UploadZone } from "@/components/kb/UploadZone";
import { ScrollArea } from "@/components/ui/scroll-area";
import { api } from "@/lib/api";
import type { KbDocument } from "@/types";

/** Knowledge Base：企业知识库管理（上传→解析→切片→向量化→检索） */
export function KnowledgeBasePage() {
  const queryClient = useQueryClient();
  const [previewDoc, setPreviewDoc] = useState<KbDocument | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);

  const { data: docs, isLoading } = useQuery({
    queryKey: ["kb-documents"],
    queryFn: api.listDocuments,
    // 有处理中任务时高频轮询状态
    refetchInterval: (query) =>
      (query.state.data ?? []).some((d) =>
        ["pending", "parsing", "embedding"].includes(d.status),
      )
        ? 3000
        : 15000,
  });
  const { data: stats } = useQuery({
    queryKey: ["kb-stats"],
    queryFn: api.kbStats,
    refetchInterval: 10000,
  });

  const uploadMutation = useMutation({
    mutationFn: api.uploadDocuments,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["kb-documents"] }),
    onError: (e: Error) => window.alert(e.message),
  });

  const deleteMutation = useMutation({
    mutationFn: api.deleteDocument,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["kb-documents"] }),
  });

  const onDelete = (doc: KbDocument) => {
    if (window.confirm(`确认删除「${doc.name}」？其 ${doc.chunk_count} 个切片将一并从向量库移除。`)) {
      deleteMutation.mutate(doc.id);
    }
  };

  const statCards = [
    { icon: Layers, label: "文档总数", value: stats?.documents ?? 0 },
    { icon: CheckCircle2, label: "已索引", value: stats?.indexed ?? 0, tint: "text-emerald-600" },
    { icon: Clock3, label: "处理中", value: stats?.processing ?? 0, tint: "text-primary" },
    { icon: XCircle, label: "失败", value: stats?.failed ?? 0, tint: "text-rose-600" },
    { icon: Layers, label: "向量切片", value: stats?.chunks ?? 0 },
  ];

  return (
    <ScrollArea className="min-w-0 flex-1">
      <div className="mx-auto max-w-[1000px] px-8 py-8">
        <h1 className="text-xl font-bold">Knowledge Base</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          企业知识库：上传文档后自动完成解析、语义切片与 bge-m3 向量化，研究报告的"查询企业知识库"
          步骤将检索这些真实内部资料
        </p>

        {stats && !stats.vector_store_ready && (
          <div className="mt-4 flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
            <FileWarning className="h-4 w-4" />
            Qdrant 向量库不可达（docker compose up -d qdrant），文档可上传但无法索引
          </div>
        )}

        {/* 统计条 */}
        <div className="mt-5 grid grid-cols-5 gap-3">
          {statCards.map(({ icon: Icon, label, value, tint }) => (
            <div key={label} className="rounded-xl border bg-card p-3.5">
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <Icon className={`h-3.5 w-3.5 ${tint ?? ""}`} />
                {label}
              </div>
              <div className="mt-1.5 text-xl font-bold tabular-nums">{value}</div>
            </div>
          ))}
        </div>

        {/* 上传区 */}
        <div className="mt-5">
          <UploadZone uploading={uploadMutation.isPending} onUpload={(files) => uploadMutation.mutate(files)} />
        </div>

        {/* 文档表格 */}
        <div className="mt-5">
          {isLoading ? (
            <div className="flex items-center justify-center gap-2 py-12 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> 加载文档列表...
            </div>
          ) : (
            <DocumentTable
              documents={docs ?? []}
              onPreview={(d) => {
                setPreviewDoc(d);
                setPreviewOpen(true);
              }}
              onDelete={onDelete}
            />
          )}
        </div>
      </div>

      <ChunkPreviewDialog doc={previewDoc} open={previewOpen} onOpenChange={setPreviewOpen} />
    </ScrollArea>
  );
}
