import { ChevronDown, ChevronUp, Eye } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatRelevance } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { SourceItem } from "@/types";
import { SourceTypeIcon } from "./SourceTypeIcon";

/** 解析 kb://doc/{id}#c{idx} → 知识库来源的文档与片段定位 */
export function parseKbUrl(url: string): { documentId: number; chunkIndex: number } | null {
  const match = /kb:\/\/doc\/(\d+)#c(\d+)/.exec(url);
  if (!match) return null;
  return { documentId: parseInt(match[1], 10), chunkIndex: parseInt(match[2], 10) };
}

/**
 * 研究页 Sources 列表项：
 * 点击卡片 → 展开 snippet 内容 + 反向联动报告 [n] 高亮；
 * 知识库来源额外提供"查看完整片段"弹窗（全文溯源）。
 */
export function SourceItemCard({
  source,
  selected,
  expanded,
  onToggle,
  onViewFull,
}: {
  source: SourceItem;
  selected: boolean;
  expanded: boolean;
  onToggle: () => void;
  onViewFull: (source: SourceItem) => void;
}) {
  const kbLoc = parseKbUrl(source.url);
  return (
    <div
      data-ref-no={source.ref_no}
      className={cn(
        "w-full max-w-full cursor-pointer rounded-xl border bg-card p-3 transition-all",
        selected && "border-primary ring-2 ring-primary/30",
        !selected && "hover:border-primary/40",
      )}
      onClick={onToggle}
    >
      <div className="flex items-start gap-2.5">
        <SourceTypeIcon type={source.type} />
        <div className="min-w-0 flex-1">
          <div className="line-clamp-2 text-[13px] font-medium leading-snug text-foreground/90">
            {source.ref_no > 0 && (
              <span className="mr-1 font-semibold text-primary">[{source.ref_no}]</span>
            )}
            {source.title}
          </div>
          <div className="mt-1.5 flex min-w-0 flex-wrap items-center gap-1.5">
            <Badge variant="muted" className="max-w-[160px] truncate px-1.5 text-[11px] font-normal">
              {source.source_label || source.type}
            </Badge>
            <span className="shrink-0 text-[11px] text-muted-foreground">
              · 相关度 {formatRelevance(source.relevance)}
            </span>
            {source.page_nos && source.page_nos.length > 0 && (
              <span className="shrink-0 text-[11px] text-muted-foreground">
                · 第{source.page_nos.join("、")}页
              </span>
            )}
            <span className="ml-auto text-[11px] text-muted-foreground">
              {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
            </span>
          </div>
        </div>
      </div>

      {expanded && (
        <div className="mt-2.5 border-t border-border/60 pt-2.5" onClick={(e) => e.stopPropagation()}>
          {/* 原生滚动区：内容超长在展开区内滚动，收起按钮始终可达 */}
          <div className="max-h-[240px] w-full max-w-full overflow-y-auto whitespace-pre-wrap pr-1 text-[12.5px] leading-relaxed text-foreground/80">
            {source.snippet || "（该来源暂无内容摘要）"}
          </div>
          <div className="mt-2 flex items-center gap-2">
            {kbLoc && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 gap-1 text-xs text-primary hover:bg-accent"
                onClick={() => onViewFull(source)}
              >
                <Eye className="h-3.5 w-3.5" />
                查看完整片段
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              className="h-7 gap-1 text-xs text-muted-foreground hover:bg-accent"
              onClick={onToggle}
            >
              <ChevronUp className="h-3.5 w-3.5" />
              收起
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
