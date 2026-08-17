import { useEffect, useMemo, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
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
export function SourcesPanel({ sources }: { sources: SourceItem[] }) {
  const [tab, setTab] = useState("All");
  const [expandedRef, setExpandedRef] = useState<number | null>(null);
  const [viewerSource, setViewerSource] = useState<SourceItem | null>(null);
  const selectedRefNo = useResearchStore((s) => s.selectedRefNo);
  const selectSource = useResearchStore((s) => s.selectSource);

  const filtered = useMemo(() => {
    const type = TAB_TYPE[tab];
    return type ? sources.filter((s) => s.type === type) : sources;
  }, [sources, tab]);

  // 报告 [n] 点击 → 定位高亮右侧来源
  useEffect(() => {
    if (selectedRefNo == null) return;
    setTab("All");
    requestAnimationFrame(() => {
      document
        .querySelector(`[data-ref-no="${selectedRefNo}"]`)
        ?.scrollIntoView({ behavior: "smooth", block: "center" });
    });
  }, [selectedRefNo]);

  const handleToggle = (refNo: number) => {
    setExpandedRef((prev) => {
      const next = prev === refNo ? null : refNo;
      // 展开时自动滚动到该卡片，保证内容顶部可见
      if (next != null) {
        requestAnimationFrame(() => {
          document
            .querySelector(`[data-ref-no="${refNo}"]`)
            ?.scrollIntoView({ behavior: "smooth", block: "nearest" });
        });
      }
      return next;
    });
    selectSource(refNo); // 反向联动：报告 [n] 高亮 + 滚动定位
  };

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="text-sm font-semibold">Sources ({sources.length})</div>
          <button className="text-xs font-medium text-primary hover:underline">View all</button>
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

        <ScrollArea className="mt-3 max-h-[380px]">
          <div className="space-y-2 pr-1">
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
        </ScrollArea>

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
