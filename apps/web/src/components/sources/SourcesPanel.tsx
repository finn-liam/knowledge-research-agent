import { memo, useEffect, useMemo, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useResearchStore } from "@/features/research/researchStore";
import type { SourceItem } from "@/types";
import { ChunkViewerDialog } from "./ChunkViewerDialog";
import { SourceItemCard } from "./SourceItemCard";

const TAB_TYPE: Record<string, SourceItem["type"] | null> = {
  All: null,
  Enterprise: "enterprise",
  Papers: "paper",
  Web: "web",
};

/** 研究页右侧「Sources (n)」面板：Tab 筛选 + 点击展开内容 + 双向引用联动 */
function SourcesPanelInner({ sources }: { sources: SourceItem[] }) {
  const [tab, setTab] = useState("All");
  const [expandedRef, setExpandedRef] = useState<number | null>(null);
  const [viewerSource, setViewerSource] = useState<SourceItem | null>(null);
  const selectedRefNo = useResearchStore((s) => s.selectedRefNo);
  const selectSource = useResearchStore((s) => s.selectSource);

  const filtered = useMemo(() => {
    const type = TAB_TYPE[tab];
    return type ? sources.filter((s) => s.type === type) : sources;
  }, [sources, tab]);

  // 报告 [n] 点击 → 定位高亮右侧来源（仅当来源被当前 Tab 过滤掉时才切回 All，点击展开箭头不跳 Tab）
  useEffect(() => {
    if (selectedRefNo == null) return;
    const visible = filtered.some((s) => s.ref_no === selectedRefNo);
    if (!visible) setTab("All");
    requestAnimationFrame(() => {
      document
        .querySelector(`[data-ref-no="${selectedRefNo}"]`)
        ?.scrollIntoView({ behavior: "smooth", block: "center", inline: "nearest" });
    });
  }, [selectedRefNo, filtered]);

  const handleToggle = (refNo: number) => {
    setExpandedRef((prev) => {
      const next = prev === refNo ? null : refNo;
      // 展开时自动滚动到该卡片，保证内容顶部可见
      if (next != null) {
        requestAnimationFrame(() => {
          document
            .querySelector(`[data-ref-no="${refNo}"]`)
            ?.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "nearest" });
        });
      }
      return next;
    });
    selectSource(refNo); // 反向联动：报告 [n] 高亮 + 滚动定位
  };

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex min-w-0 items-center justify-between gap-3">
          <div className="min-w-0 truncate text-sm font-semibold">Sources ({sources.length})</div>
          <button className="shrink-0 whitespace-nowrap text-xs font-medium text-primary hover:underline">
            View all
          </button>
        </div>

        <Tabs value={tab} onValueChange={setTab} className="mt-3">
          <TabsList className="h-8 w-full justify-start gap-1 bg-transparent p-0">
            {Object.keys(TAB_TYPE).map((name) => (
              <TabsTrigger
                key={name}
                value={name}
                className="h-7 rounded-full px-3 text-xs data-[state=active]:bg-accent"
              >
                {name}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>

        {/* 列表随右栏自然滚动（移除嵌套 ScrollArea，避免滚轮被多层容器吃掉） */}
        <div className="mt-3 space-y-2 pr-1">
          {filtered.map((s) => (
            <SourceItemCard
              key={`${s.ref_no}-${s.title}`}
              source={s}
              selected={s.ref_no === selectedRefNo}
              expanded={s.ref_no === expandedRef}
              onToggle={() => handleToggle(s.ref_no)}
              onViewFull={setViewerSource}
            />
          ))}
          {filtered.length === 0 && (
            <div className="py-6 text-center text-xs text-muted-foreground">
              该分类下暂无来源
            </div>
          )}
        </div>

        <button className="mt-3 w-full text-center text-xs font-medium text-primary hover:underline">
          Show all {sources.length} sources →
        </button>
      </CardContent>

      <ChunkViewerDialog
        source={viewerSource}
        open={!!viewerSource}
        onOpenChange={(v) => !v && setViewerSource(null)}
      />
    </Card>
  );
}

/** memo：来源列表在流式期间基本稳定，避免随 reportBuffer 变化重渲染 */
export const SourcesPanel = memo(SourcesPanelInner);
