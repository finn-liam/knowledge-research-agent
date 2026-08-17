import { useQuery } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { GraphMiniPanel } from "@/components/graph/GraphMiniPanel";
import { RightPanel } from "@/components/layout/RightPanel";
import { ExampleCards } from "@/components/research/ExampleCards";
import { ResearchComposer } from "@/components/research/ResearchComposer";
import { SourcesStatsPanel } from "@/components/sources/SourcesStatsPanel";
import { ResearchStatsPanel } from "@/components/stats/ResearchStatsPanel";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useUserStore } from "@/features/user/userStore";
import { api } from "@/lib/api";

/** 首页：欢迎区 + 研究输入框 + 示例卡片 + 右侧三面板（对齐效果图1） */
export function HomePage() {
  const navigate = useNavigate();
  const reportLang = useUserStore((s) => s.reportLang);

  const { data: sourceStats } = useQuery({
    queryKey: ["source-stats"],
    queryFn: api.sourceStats,
  });
  const { data: summary } = useQuery({
    queryKey: ["analytics-summary"],
    queryFn: api.analyticsSummary,
  });

  const startResearch = async (query: string) => {
    const { task_id } = await api.createResearch(query, reportLang);
    navigate(`/research/${task_id}`);
  };

  return (
    <>
      <ScrollArea className="min-w-0 flex-1">
        <div className="mx-auto max-w-[860px] px-8 pb-16 pt-14">
          {/* 欢迎区 */}
          <div className="text-center">
            <h1 className="flex items-center justify-center gap-2 text-[28px] font-bold tracking-tight">
              Welcome to Knowledge Research Agent
              <Sparkles className="h-6 w-6 text-primary" />
            </h1>
            <p className="mt-2.5 text-[15px] text-muted-foreground">
              Your AI-powered assistant for enterprise knowledge research and analysis
            </p>
          </div>

          {/* 研究输入框 */}
          <div className="mt-8">
            <ResearchComposer variant="hero" onSubmit={startResearch} />
          </div>

          {/* 示例问题 */}
          <div className="mt-10">
            <div className="mb-3.5 text-center text-sm font-medium text-muted-foreground">
              Try these examples
            </div>
            <ExampleCards onPick={startResearch} />
          </div>
        </div>
      </ScrollArea>

      <RightPanel>
        <SourcesStatsPanel items={sourceStats?.items ?? []} />
        <GraphMiniPanel graph={{ nodes: [], edges: [] }} />
        <ResearchStatsPanel summary={summary} />
      </RightPanel>
    </>
  );
}
