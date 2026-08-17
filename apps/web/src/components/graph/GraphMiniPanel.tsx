import { memo } from "react";
import { Card, CardContent } from "@/components/ui/card";
import type { GraphData } from "@/types";
import { GraphCanvas } from "./GraphCanvas";
import { GraphEmptyState } from "./GraphEmptyState";

/** 右侧「Knowledge Graph」面板：空态插画 / 有数据时渲染迷你图谱（首页、研究页复用） */
function GraphMiniPanelInner({ graph, hint }: { graph: GraphData; hint?: string }) {
  const hasData = graph.nodes.length > 0;
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="text-sm font-semibold">Knowledge Graph</div>
          <button className="text-xs font-medium text-primary hover:underline">
            View full graph
          </button>
        </div>
        <div className="mt-2">
          {hasData ? <GraphCanvas graph={graph} /> : <GraphEmptyState hint={hint} />}
        </div>
      </CardContent>
    </Card>
  );
}

/** memo：图谱面板不随流式 token 变化重渲染 */
export const GraphMiniPanel = memo(GraphMiniPanelInner);
